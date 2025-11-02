import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import random, datetime
import mysql.connector
import os

# ------------------- DATABASE CONNECTION ------------------- #
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Adcet@123",  # change as per your setup
    database="canteen_db"
)
cursor = db.cursor(dictionary=True)

# ------------------- GLOBAL VARIABLES ------------------- #
quantities = {}
images = {}
menu_items = {}

# ------------------- LOAD MENU ------------------- #
def load_menu():
    global menu_items
    menu_items.clear()
    cursor.execute("SELECT * FROM menu_items")
    rows = cursor.fetchall()
    for row in rows:
        menu_items[row['name']] = {"price": row['price'], "image": row['image']}

# ------------------- SCROLLABLE FRAME ------------------- #
class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self, bg="#fef9f0")
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="#fef9f0")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="n")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

# ------------------- RELOAD ORDERING PAGE ------------------- #
def reload_ordering_page():
    # Clear old cards
    for widget in scroll_frame.scrollable_frame.winfo_children():
        widget.destroy()

    load_menu()  # reload menu from DB

    row = 0
    col = 0
    for item, info in menu_items.items():
        card = tk.Frame(scroll_frame.scrollable_frame, bg="white", bd=2, relief="raised", width=220, height=280)
        card.grid(row=row, column=col, padx=20, pady=20)
        card.grid_propagate(False)

        img = Image.open(info["image"])
        img = img.resize((160, 160), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        images[item] = photo  # keep persistent reference
        tk.Label(card, image=photo, bg="white").pack(pady=10)

        tk.Label(card, text=item, font=("Arial", 16, "bold"), bg="white").pack()
        tk.Label(card, text=f"₹{info['price']}", font=("Arial", 14), bg="white", fg="green").pack()

        var = tk.IntVar()
        tk.Spinbox(card, from_=0, to=10, textvariable=var, width=5, font=("Arial", 12)).pack(pady=10)
        quantities[item] = var

        col += 1
        if col > 3:
            col = 0
            row += 1

# ------------------- GENERATE BILL ------------------- #
def generate_bill():
    any_item = False
    for var in quantities.values():
        if var.get() > 0:
            any_item = True
            break

    if not any_item:
        messagebox.showwarning("No Order", "Please select at least one item!")
        return  # exit function if nothing selected

    # If at least one item is selected, proceed to ask details
    def submit_details():
        nonlocal buyer_name, mobile
        buyer_name = name_var.get().strip()
        mobile = mobile_var.get().strip()
        if not buyer_name or not mobile:
            messagebox.showwarning("Input Error", "Please enter both name and mobile!")
            return
        details_win.destroy()
        create_bill_window()

    buyer_name = ""
    mobile = ""
    details_win = tk.Toplevel(root)
    details_win.title("Enter Details")
    details_win.geometry("400x250")
    details_win.configure(bg="#fef9f0")

    tk.Label(details_win, text="Enter Your Details", font=("Arial", 18, "bold"), bg="#fef9f0").pack(pady=10)
    tk.Label(details_win, text="Name:", font=("Arial", 14), bg="#fef9f0").pack(pady=5)
    name_var = tk.StringVar()
    tk.Entry(details_win, textvariable=name_var, font=("Arial", 12)).pack(pady=5)
    tk.Label(details_win, text="Mobile:", font=("Arial", 14), bg="#fef9f0").pack(pady=5)
    mobile_var = tk.StringVar()
    tk.Entry(details_win, textvariable=mobile_var, font=("Arial", 12)).pack(pady=5)
    tk.Button(details_win, text="Submit", command=submit_details, bg="#8bc34a", fg="white", font=("Arial", 14)).pack(pady=15)

    def create_bill_window():
        total = 0
        order_details = []
        any_item = False
        for item, var in quantities.items():
            qty = var.get()
            if qty > 0:
                any_item = True
                price = menu_items[item]["price"] * qty
                total += price
                order_details.append((item, qty, price))
        if not any_item:
            messagebox.showwarning("No Order", "Please select at least one item!")
            return

        bill_id = f"BILL{random.randint(1000,9999)}"
        date = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        # Save bill to database
        cursor.execute("INSERT INTO bills (bill_id, buyer_name, mobile, date, total) VALUES (%s,%s,%s,%s,%s)",
                       (bill_id, buyer_name, mobile, datetime.datetime.now(), total))
        db.commit()

        # Save each item in bill_items table
        for item, qty, price in order_details:
            cursor.execute("INSERT INTO bill_items (bill_id, item_name, quantity, price) VALUES (%s,%s,%s,%s)",
                           (bill_id, item, qty, price))
        db.commit()

        messagebox.showinfo("Order Placed", "Your order has been successfully placed!")

        # Bill Window
        bill_window = tk.Toplevel(root)
        bill_window.title("Bill Receipt")
        bill_window.state('zoomed')
        bill_window.configure(bg="#fef9f0")

        tk.Label(bill_window, text="🍽️ CANTEEN BILL 🍽️", font=("Arial", 32, "bold"), bg="#fef9f0").pack(pady=30)

        frame = tk.Frame(bill_window, bg="white", bd=3, relief="solid")
        frame.pack(padx=50, pady=30, fill=tk.BOTH, expand=True)

        tk.Label(frame, text=f"Bill ID: {bill_id}    Date: {date}", font=("Arial", 16), bg="white").pack(pady=10)
        tk.Label(frame, text=f"Buyer: {buyer_name}    Mobile: {mobile}", font=("Arial", 16), bg="white").pack(pady=5)
        tk.Label(frame, text=f"{'Item':<20}{'Qty':<10}{'Price':<10}", font=("Consolas", 16, "bold"), bg="white").pack(anchor="w", padx=20)

        for item, qty, price in order_details:
            tk.Label(frame, text=f"{item:<20}{qty:<10}{price:<10}", font=("Consolas", 16), bg="white").pack(anchor="w", padx=20)

        tk.Label(frame, text="-"*50, font=("Consolas", 16), bg="white").pack(pady=5)
        tk.Label(frame, text=f"TOTAL AMOUNT: ₹{total}", font=("Arial", 24, "bold"), bg="white", fg="green").pack(pady=10)
        tk.Label(frame, text="Thank You! Visit Again 😊", font=("Arial", 18), bg="white").pack(pady=10)

# ------------------- ADMIN PANEL ------------------- #
def admin_panel():
    load_menu()
    admin_win = tk.Toplevel(root)
    admin_win.title("Admin Panel")
    admin_win.state('zoomed')
    admin_win.configure(bg="#fef9f0")

    tk.Label(admin_win, text="🛠️ Admin Panel 🛠️", font=("Arial", 32, "bold"), bg="#fef9f0").pack(pady=20)

    # ---------- Add New Item ----------
    def add_new_item():
        popup = tk.Toplevel(admin_win)
        popup.title("Add New Item")
        popup.geometry("400x300")
        popup.configure(bg="#fef9f0")

        tk.Label(popup, text="Item Name:", font=("Arial", 14), bg="#fef9f0").pack(pady=5)
        name_var = tk.StringVar()
        tk.Entry(popup, textvariable=name_var, font=("Arial", 12)).pack(pady=5)

        tk.Label(popup, text="Price:", font=("Arial", 14), bg="#fef9f0").pack(pady=5)
        price_var = tk.IntVar()
        tk.Entry(popup, textvariable=price_var, font=("Arial", 12)).pack(pady=5)

        img_var = tk.StringVar()
        def choose_image():
            file = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
            if file:
                img_var.set(os.path.basename(file))
                # Copy image to working folder
                os.replace(file, os.path.basename(file))
                messagebox.showinfo("Image Selected", "Image selected successfully!")

        tk.Button(popup, text="Choose Image", command=choose_image, bg="#03a9f4", fg="white").pack(pady=5)

        # Save button
        def save_new_item():
            if name_var.get() and price_var.get() and img_var.get():
                cursor.execute("INSERT INTO menu_items (name, price, image) VALUES (%s,%s,%s)",
                               (name_var.get(), price_var.get(), img_var.get()))
                db.commit()
                messagebox.showinfo("Added", f"{name_var.get()} added successfully!")
                popup.destroy()  # close popup only after saving
                admin_win.destroy()  # refresh admin panel
                admin_panel()
            else:
                messagebox.showwarning("Incomplete", "All fields are required!")

        tk.Button(popup, text="Save", command=save_new_item, bg="#4caf50", fg="white").pack(pady=10)
        tk.Button(popup, text="Cancel", command=popup.destroy, bg="#f44336", fg="white").pack(pady=5)

    tk.Button(admin_win, text="Add New Item", command=add_new_item, bg="#8bc34a", fg="white",
              font=("Arial", 16, "bold")).pack(pady=10)

    # ---------- View Bills ----------
    def view_bills():
        bills_win = tk.Toplevel(admin_win)
        bills_win.title("All Previous Bills")
        bills_win.state('zoomed')
        bills_win.configure(bg="#fef9f0")

        tk.Label(bills_win, text="📄 Previous Bills 📄", font=("Arial", 32, "bold"), bg="#fef9f0").pack(pady=20)

        frame = tk.Frame(bills_win, bg="white")
        frame.pack(fill="both", expand=True, padx=50, pady=20)

        canvas = tk.Canvas(frame, bg="white")
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="white")

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        headers = ["Bill ID", "Buyer Name", "Mobile", "Date", "Total Amount"]
        for i, h in enumerate(headers):
            tk.Label(scroll_frame, text=h, font=("Arial", 14, "bold"), bg="#3e2723", fg="white",
                     width=20, borderwidth=1, relief="solid").grid(row=0, column=i)

        cursor.execute("SELECT * FROM bills ORDER BY date DESC")
        rows = cursor.fetchall()
        for r, row_data in enumerate(rows, start=1):
            bg_color = "#f9fbe7" if r % 2 == 0 else "white"
            tk.Label(scroll_frame, text=row_data['bill_id'], bg=bg_color, width=20, borderwidth=1, relief="solid").grid(row=r, column=0)
            tk.Label(scroll_frame, text=row_data['buyer_name'], bg=bg_color, width=20, borderwidth=1, relief="solid").grid(row=r, column=1)
            tk.Label(scroll_frame, text=row_data['mobile'], bg=bg_color, width=20, borderwidth=1, relief="solid").grid(row=r, column=2)
            tk.Label(scroll_frame, text=row_data['date'], bg=bg_color, width=20, borderwidth=1, relief="solid").grid(row=r, column=3)
            tk.Label(scroll_frame, text=f"₹{row_data['total']}", bg=bg_color, width=20, borderwidth=1, relief="solid").grid(row=r, column=4)

    tk.Button(admin_win, text="View Bills", command=view_bills, bg="#03a9f4", fg="white",
              font=("Arial", 16, "bold")).pack(pady=10)

    # ---------- Admin Menu Cards ----------
    scroll_frame_admin = ScrollableFrame(admin_win)
    scroll_frame_admin.pack(fill="both", expand=True, padx=20, pady=10)

    row = 0
    col = 0
    for item, info in menu_items.items():
        card = tk.Frame(scroll_frame_admin.scrollable_frame, bg="white", bd=2, relief="raised", width=220, height=280)
        card.grid(row=row, column=col, padx=20, pady=20)
        card.grid_propagate(False)

        img = Image.open(info["image"])
        img = img.resize((160, 160), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        images[item] = photo
        tk.Label(card, image=photo, bg="white").pack(pady=10)

        tk.Label(card, text=item, font=("Arial", 16, "bold"), bg="white").pack()
        price_var = tk.IntVar(value=info["price"])
        tk.Entry(card, textvariable=price_var, font=("Arial", 14), width=8, justify="center").pack(pady=5)

        def browse_image(name=item):
            file = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
            if file:
                menu_items[name]["image"] = os.path.basename(file)
                os.replace(file, os.path.basename(file))
                admin_win.destroy()
                admin_panel()

        tk.Button(card, text="Change Image", command=browse_image, bg="#03a9f4", fg="white").pack(pady=2)

        def update_item(name=item, var=price_var):
            cursor.execute("UPDATE menu_items SET price=%s, image=%s WHERE name=%s",
                           (var.get(), menu_items[name]["image"], name))
            db.commit()
            messagebox.showinfo("Updated", f"{name} updated successfully!")

        tk.Button(card, text="Save", command=update_item, bg="#4caf50", fg="white").pack(pady=2)

        def delete_item(name=item):
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {name}?"):
                cursor.execute("DELETE FROM menu_items WHERE name=%s", (name,))
                db.commit()
                admin_win.destroy()
                admin_panel()

        tk.Button(card, text="Delete", command=delete_item, bg="#f44336", fg="white").pack(pady=2)

        col += 1
        if col > 3:
            col = 0
            row += 1

    tk.Button(admin_win, text="Back", bg="#9e9e9e", fg="white", font=("Arial", 16, "bold"),
              command=lambda: [admin_win.destroy(), reload_ordering_page()]).pack(pady=20)

# ------------------- ADMIN LOGIN ------------------- #
def admin_login():
    login_win = tk.Toplevel(root)
    login_win.title("Admin Login")
    login_win.geometry("400x300")
    login_win.configure(bg="#fef9f0")

    tk.Label(login_win, text="Admin Login", font=("Arial", 20, "bold"), bg="#fef9f0").pack(pady=20)

    tk.Label(login_win, text="Username", font=("Arial", 14), bg="#fef9f0").pack()
    username_var = tk.StringVar()
    tk.Entry(login_win, textvariable=username_var, font=("Arial", 12)).pack(pady=5)

    tk.Label(login_win, text="Password", font=("Arial", 14), bg="#fef9f0").pack()
    password_var = tk.StringVar()
    tk.Entry(login_win, textvariable=password_var, font=("Arial", 12), show="*").pack(pady=5)

    def check_login():
        cursor.execute("SELECT * FROM admin WHERE username=%s AND password=%s",
                       (username_var.get(), password_var.get()))
        result = cursor.fetchone()
        if result:
            messagebox.showinfo("Login Success", "Welcome Admin!")
            login_win.destroy()
            admin_panel()
        else:
            messagebox.showerror("Login Failed", "Invalid credentials!")

    tk.Button(login_win, text="Login", bg="#8bc34a", fg="white", font=("Arial", 14, "bold"),
              command=check_login).pack(pady=20)

# ------------------- MAIN WINDOW ------------------- #
root = tk.Tk()
root.title("Canteen Food Ordering System")
root.state('zoomed')
root.configure(bg="#fef9f0")

tk.Label(root, text="🍽️ College Canteen 🍽️", font=("Arial", 36, "bold"), bg="#fef9f0", fg="#3e2723").pack(pady=20)

tk.Button(root, text="Admin Login", bg="#ff9800", fg="white",
          font=("Arial", 16, "bold"), command=admin_login).pack(pady=10)

load_menu()
scroll_frame = ScrollableFrame(root)
scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

reload_ordering_page()  # initial load

tk.Button(root, text="Place Order & Generate Bill", bg="#8bc34a", fg="white",
          font=("Arial", 18, "bold"), command=generate_bill).pack(pady=20)

root.mainloop()