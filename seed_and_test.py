


import requests
import json
import subprocess
import os
import sys
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_step(name: str):
    print(f"\n[{time.strftime('%H:%M:%S')}] *** {name}")

def assert_status(res: requests.Response, expected: int, msg: str = ""):
    if res.status_code != expected:
        print(f"FAILED: {msg}")
        print(f"Expected {expected}, got {res.status_code}")
        print(res.text)
        sys.exit(1)
    else:
        print(f"PASS: {msg}")

def main():
    print_step("Seeding Categories via psql")
    env = os.environ.copy()
    env["PGPASSWORD"] = "1234"

    psql_base = [
        r"C:\Program Files\PostgreSQL\18\bin\psql.exe",
        "-U",
        "postgres",
        "-d",
        "finance_db"
    ]

    subprocess.run(
        psql_base + ["-c", "TRUNCATE TABLE financial_records, users CASCADE;"],
        env=env
    )

    categories = [
        "Salary",
        "Rent",
        "Groceries",
        "Transport",
        "Freelance",
        "Shopping",
        "Travel",
        "Utilities",
        "Bonus",
        "Medical",
        "Entertainment",
        "Investments"
    ]

    for c in categories:
        subprocess.run(
            psql_base + [
                "-c",
                f"INSERT INTO categories (name) VALUES ('{c}') ON CONFLICT DO NOTHING;"
            ],
            env=env,
            stdout=subprocess.DEVNULL
        )

    print_step("1. Register Users")

    users = {
        "admin_user": {
            "email": "admin@finance.com",
            "username": "admin_user",
            "full_name": "System Admin",
            "password": "Admin@123",
            "role": "ADMIN",
            "is_active": True
        },
        "analyst_user": {
            "email": "analyst@finance.com",
            "username": "finance_analyst",
            "full_name": "Riya Sharma",
            "password": "Analyst@123",
            "role": "ANALYST",
            "is_active": True
        },
        "viewer_user": {
            "email": "viewer@finance.com",
            "username": "dashboard_viewer",
            "full_name": "Aman Gupta",
            "password": "Viewer@123",
            "role": "VIEWER",
            "is_active": True
        },
        "inactive_user": {
            "email": "inactive@finance.com",
            "username": "inactive_user",
            "full_name": "Inactive Member",
            "password": "Inactive@123",
            "role": "VIEWER",
            "is_active": False
        }
    }

    for key, data in users.items():
        res = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": data["email"],
                "username": data["username"],
                "password": data["password"],
                "full_name": data["full_name"]
            }
        )
        assert_status(res, 201, f"Register {key}")

        updates = f"UPDATE users SET role='{data['role']}'"
        if not data["is_active"]:
            updates += ", status='INACTIVE'"
        updates += f" WHERE email='{data['email']}';"

        subprocess.run(
            psql_base + ["-c", updates],
            env=env,
            stdout=subprocess.DEVNULL
        )

    print_step("2. Test Exact Scenarios")

    # Duplicate email
    res = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": "admin@finance.com",
            "username": "admin2",
            "password": "password"
        }
    )
    assert_status(res, 409, "Register duplicate email")

    # Wrong password
    res = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "admin@finance.com",
            "password": "WrongPassword"
        }
    )
    assert_status(res, 401, "Login wrong password")

    # Inactive user
    res = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "inactive@finance.com",
            "password": "Inactive@123"
        }
    )
    assert_status(res, 401, "Login inactive user")

    assert "User account is inactive" in res.text
    print("PASS: Inactive user error message matches precisely")

    # Get tokens
    admin_token = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "admin@finance.com",
            "password": "Admin@123"
        }
    ).json()["access_token"]

    analyst_token = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "analyst@finance.com",
            "password": "Analyst@123"
        }
    ).json()["access_token"]

    viewer_token = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "viewer@finance.com",
            "password": "Viewer@123"
        }
    ).json()["access_token"]

    admin_h = {"Authorization": f"Bearer {admin_token}"}
    analyst_h = {"Authorization": f"Bearer {analyst_token}"}
    viewer_h = {"Authorization": f"Bearer {viewer_token}"}

    print_step("3. Seed Financial Records via Admin")

    records = [
        {"amount": 85000, "type": "INCOME", "category": "Salary", "date": "2026-01-05T00:00:00Z", "description": "January salary credited"},
        {"amount": 12000, "type": "EXPENSE", "category": "Rent", "date": "2026-01-06T00:00:00Z", "description": "Monthly apartment rent"},
        {"amount": 3500, "type": "EXPENSE", "category": "Groceries", "date": "2026-01-08T00:00:00Z", "description": "Weekly grocery shopping"},
        {"amount": 2500, "type": "EXPENSE", "category": "Transport", "date": "2026-01-10T00:00:00Z", "description": "Fuel and cab charges"},
        {"amount": 15000, "type": "INCOME", "category": "Freelance", "date": "2026-01-15T00:00:00Z", "description": "Website development project payment"},
        {"amount": 7000, "type": "EXPENSE", "category": "Shopping", "date": "2026-01-18T00:00:00Z", "description": "Clothes and accessories"},
        {"amount": 9000, "type": "EXPENSE", "category": "Travel", "date": "2026-02-02T00:00:00Z", "description": "Weekend trip expenses"},
        {"amount": 85000, "type": "INCOME", "category": "Salary", "date": "2026-02-05T00:00:00Z", "description": "February salary credited"},
        {"amount": 12000, "type": "EXPENSE", "category": "Rent", "date": "2026-02-06T00:00:00Z", "description": "Monthly apartment rent"},
        {"amount": 5000, "type": "EXPENSE", "category": "Utilities", "date": "2026-02-09T00:00:00Z", "description": "Electricity, internet, water bills"},
        {"amount": 18000, "type": "INCOME", "category": "Bonus", "date": "2026-02-12T00:00:00Z", "description": "Performance bonus"},
        {"amount": 4000, "type": "EXPENSE", "category": "Medical", "date": "2026-02-14T00:00:00Z", "description": "Doctor consultation and medicines"},
        {"amount": 85000, "type": "INCOME", "category": "Salary", "date": "2026-03-05T00:00:00Z", "description": "March salary credited"},
        {"amount": 12000, "type": "EXPENSE", "category": "Rent", "date": "2026-03-06T00:00:00Z", "description": "Monthly apartment rent"},
        {"amount": 4500, "type": "EXPENSE", "category": "Entertainment", "date": "2026-03-11T00:00:00Z", "description": "Movies and dining out"},
        {"amount": 22000, "type": "INCOME", "category": "Investments", "date": "2026-03-15T00:00:00Z", "description": "Mutual fund profit withdrawal"},
        {"amount": 3000, "type": "EXPENSE", "category": "Transport", "date": "2026-03-18T00:00:00Z", "description": "Metro card and fuel recharge"}
    ]

    record_ids = []

    for r in records:
        cat_res = subprocess.run(
            psql_base + ["-t", "-c", f"SELECT id FROM categories WHERE name='{r['category']}';"],
            capture_output=True,
            text=True,
            env=env
        )

        assert cat_res.stdout.strip(), f"Category not found: {r['category']}"
        cat_id = int(cat_res.stdout.strip())

        res = requests.post(
            f"{BASE_URL}/records/",
            headers=admin_h,
            json={
                "amount": r["amount"],
                "type": r["type"],
                "category_id": cat_id,
                "date": r["date"],
                "description": r["description"]
            }
        )

        assert_status(res, 201, f"Create record {r['category']}")
        record_ids.append(res.json()["id"])

    print(f"PASS: Inserted {len(records)} records")

    print_step("4. Test Role-Based Restrictions on Records")

    # Viewer cannot create
    res = requests.post(
        f"{BASE_URL}/records/",
        headers=viewer_h,
        json={
            "amount": 100,
            "type": "EXPENSE",
            "category_id": cat_id,
            "date": "2026-01-01T00:00:00Z"
        }
    )
    assert_status(res, 403, "Viewer tries POST /records")

    # Analyst can create
    res = requests.post(
        f"{BASE_URL}/records/",
        headers=analyst_h,
        json={
            "amount": 2500,
            "type": "EXPENSE",
            "category_id": cat_id,
            "date": "2026-03-20T00:00:00Z",
            "description": "Analyst test record"
        }
    )
    assert_status(res, 201, "Analyst can create record")

    # Analyst cannot delete
    res = requests.delete(
        f"{BASE_URL}/records/{record_ids[0]}",
        headers=analyst_h
    )
    assert_status(res, 403, "Analyst tries DELETE /records")

    # Admin soft delete
    res = requests.post(
        f"{BASE_URL}/records/",
        headers=admin_h,
        json={
            "amount": 100,
            "type": "EXPENSE",
            "category_id": cat_id,
            "date": "2026-01-01T00:00:00Z"
        }
    )
    dummy_id = res.json()["id"]

    res = requests.delete(
        f"{BASE_URL}/records/{dummy_id}",
        headers=admin_h
    )
    assert_status(res, 200, "Admin soft deletes a record")

    print_step("5. Test Unauthenticated Access")

    res = requests.get(f"{BASE_URL}/records/")
    assert_status(res, 403, "Unauthenticated access to records")

    print_step("6. Test Record Filters")

    res = requests.get(
        f"{BASE_URL}/records/?category=Rent",
        headers=viewer_h
    )
    assert_status(res, 200, "Filter by category: Rent")
    print(f"Found {len(res.json()['items'])} Rent items")

    res = requests.get(
        f"{BASE_URL}/records/?type=EXPENSE",
        headers=viewer_h
    )
    assert_status(res, 200, "Filter by type: EXPENSE")
    print(f"Found {len(res.json()['items'])} Expense items")

    res = requests.get(
        f"{BASE_URL}/records/?start_date=2026-02-01T00:00:00Z&end_date=2026-02-28T23:59:59Z",
        headers=analyst_h
    )
    assert_status(res, 200, "Filter by date range: Feb 2026")
    print(f"Found {len(res.json()['items'])} items in Feb")

    print_step("7. Test Dashboard Output")

    res = requests.get(
        f"{BASE_URL}/dashboard/summary",
        headers=viewer_h
    )
    assert_status(res, 200, "Dashboard Summary")

    summary = res.json()
    print(json.dumps(summary, indent=2))

    assert summary["total_income"] == 310000
    assert summary["total_expenses"] == 77000  # 74500 + 2500 from the Analyst POST earlier
    assert summary["net_balance"] == 233000  # 310000 - 77000
    print("PASS: Dashboard totals correct")

    res = requests.get(
        f"{BASE_URL}/dashboard/by-category",
        headers=viewer_h
    )
    assert_status(res, 200, "Dashboard Categories")

    category_data = res.json()
    print("Categories High to Low:")
    print([
        f"{x['category_name']}: Income={x['total_income']}, Expense={x['total_expenses']}"
        for x in category_data
    ])

    res = requests.get(
        f"{BASE_URL}/dashboard/recent",
        headers=viewer_h
    )
    assert_status(res, 200, "Recent Transactions")

    recent = res.json()
    assert len(recent) <= 10
    print("PASS: Recent transactions limited to 10")

    print("\nALL custom scenarios passed perfectly!")

if __name__ == "__main__":
    main()