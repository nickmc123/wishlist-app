"""
WISHLIST - Vape Cartridge Shop
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import hashlib
import secrets
import os

app = FastAPI(title="Wishlist")

# In-memory storage (would use DB in production)
users_db = {}
sessions_db = {}
wishlists_db = {}  # user_id -> [product_ids]
favorites_db = {}  # user_id -> [product_ids]

# Demo account - pre-populated
demo_user = {
    "id": "demo_user_001",
    "email": "demo@wishlist.app",
    "name": "Demo User",
    "password_hash": hashlib.sha256("demo123".encode()).hexdigest(),
    "is_premium": True  # Premium so they can see all products
}
users_db["demo@wishlist.app"] = demo_user
wishlists_db["demo_user_001"] = [1, 3, 5]  # Cloud Chaser, Terp Tank, Midnight Black
favorites_db["demo_user_001"] = [2, 7]  # Stealth Pod, Gold Reserve

# Demo products - using Picsum for reliable images
PRODUCTS = [
    {"id": 1, "name": "Cloud Chaser 510", "price": 24.99, "category": "510 Thread", "image": "https://picsum.photos/seed/vape1/400/300", "description": "Premium 510 thread cartridge, ceramic coil", "premium_only": False},
    {"id": 2, "name": "Stealth Pod Pro", "price": 29.99, "category": "Pod System", "image": "https://picsum.photos/seed/vape2/400/300", "description": "Compact pod with adjustable airflow", "premium_only": False},
    {"id": 3, "name": "Terp Tank Elite", "price": 34.99, "category": "510 Thread", "image": "https://picsum.photos/seed/vape3/400/300", "description": "Glass tank, quartz heating element", "premium_only": False},
    {"id": 4, "name": "Vapor King XL", "price": 39.99, "category": "510 Thread", "image": "https://picsum.photos/seed/vape4/400/300", "description": "Extra large capacity, long-lasting", "premium_only": False},
    {"id": 5, "name": "Midnight Black Cart", "price": 27.99, "category": "510 Thread", "image": "https://picsum.photos/seed/vape5/400/300", "description": "Sleek black design, ceramic core", "premium_only": False},
    {"id": 6, "name": "Crystal Clear Pod", "price": 32.99, "category": "Pod System", "image": "https://picsum.photos/seed/vape6/400/300", "description": "See-through design, leak-proof", "premium_only": False},
    {"id": 7, "name": "Gold Reserve 510", "price": 49.99, "category": "Premium", "image": "https://picsum.photos/seed/gold7/400/300", "description": "24K gold contacts, lifetime warranty", "premium_only": True},
    {"id": 8, "name": "Diamond Series Cart", "price": 59.99, "category": "Premium", "image": "https://picsum.photos/seed/diamond8/400/300", "description": "Diamond-cut glass, titanium coil", "premium_only": True},
    {"id": 9, "name": "Platinum Pod Ultra", "price": 54.99, "category": "Premium", "image": "https://picsum.photos/seed/plat9/400/300", "description": "Premium materials, exclusive design", "premium_only": True},
    {"id": 10, "name": "Limited Edition Rose", "price": 69.99, "category": "Premium", "image": "https://picsum.photos/seed/rose10/400/300", "description": "Rose gold finish, collectors item", "premium_only": True},
]

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

class LoginRequest(BaseModel):
    email: str
    password: str

class WishlistAction(BaseModel):
    product_id: int

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_current_user(token: str = None):
    if not token or token not in sessions_db:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return sessions_db[token]

@app.post("/auth/register")
def register(req: RegisterRequest):
    if req.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = len(users_db) + 1
    users_db[req.email] = {
        "id": user_id,
        "email": req.email,
        "name": req.name,
        "password_hash": hash_password(req.password),
        "is_premium": False
    }
    wishlists_db[user_id] = []
    favorites_db[user_id] = []
    
    token = secrets.token_hex(32)
    sessions_db[token] = users_db[req.email]
    
    return {"ok": True, "token": token, "user": {"name": req.name, "email": req.email, "is_premium": False}}

@app.post("/auth/login")
def login(req: LoginRequest):
    user = users_db.get(req.email)
    if not user or user["password_hash"] != hash_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = secrets.token_hex(32)
    sessions_db[token] = user
    
    return {"ok": True, "token": token, "user": {"name": user["name"], "email": user["email"], "is_premium": user["is_premium"]}}

@app.post("/auth/upgrade")
def upgrade_to_premium(token: str):
    user = get_current_user(token)
    user["is_premium"] = True
    return {"ok": True, "message": "Welcome to Premium! 👑"}

@app.get("/products")
def get_products(token: str = None):
    user = None
    try:
        user = get_current_user(token)
    except:
        pass
    
    is_premium = user["is_premium"] if user else False
    
    products = []
    for p in PRODUCTS:
        product = p.copy()
        if p["premium_only"] and not is_premium:
            product["locked"] = True
        else:
            product["locked"] = False
        products.append(product)
    
    return {"products": products}

@app.get("/wishlist")
def get_wishlist(token: str):
    user = get_current_user(token)
    user_id = user["id"]
    wishlist_ids = wishlists_db.get(user_id, [])
    items = [p for p in PRODUCTS if p["id"] in wishlist_ids]
    return {"items": items}

@app.post("/wishlist/add")
def add_to_wishlist(req: WishlistAction, token: str):
    user = get_current_user(token)
    user_id = user["id"]
    
    if user_id not in wishlists_db:
        wishlists_db[user_id] = []
    
    if req.product_id not in wishlists_db[user_id]:
        wishlists_db[user_id].append(req.product_id)
    
    return {"ok": True, "message": "Added to wishlist! 💫"}

@app.post("/wishlist/remove")
def remove_from_wishlist(req: WishlistAction, token: str):
    user = get_current_user(token)
    user_id = user["id"]
    
    if user_id in wishlists_db and req.product_id in wishlists_db[user_id]:
        wishlists_db[user_id].remove(req.product_id)
    
    return {"ok": True, "message": "Removed from wishlist"}

@app.get("/favorites")
def get_favorites(token: str):
    user = get_current_user(token)
    user_id = user["id"]
    favorite_ids = favorites_db.get(user_id, [])
    items = [p for p in PRODUCTS if p["id"] in favorite_ids]
    return {"items": items}

@app.post("/favorites/add")
def add_to_favorites(req: WishlistAction, token: str):
    user = get_current_user(token)
    user_id = user["id"]
    
    if user_id not in favorites_db:
        favorites_db[user_id] = []
    
    if req.product_id not in favorites_db[user_id]:
        favorites_db[user_id].append(req.product_id)
    
    return {"ok": True, "message": "Added to favorites! ⭐"}

@app.post("/favorites/remove")
def remove_from_favorites(req: WishlistAction, token: str):
    user = get_current_user(token)
    user_id = user["id"]
    
    if user_id in favorites_db and req.product_id in favorites_db[user_id]:
        favorites_db[user_id].remove(req.product_id)
    
    return {"ok": True, "message": "Removed from favorites"}

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
