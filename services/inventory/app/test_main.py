"""
Integration tests for Inventory service routers using TestClient.
We mint JWTs locally using the service's JWT secret (settings.JWT_SECRET).
Comprehensive test coverage for MVP delivery including all CRUD operations,
purchase flows, bundle management, and edge cases.
"""

import uuid
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from jose import jwt
import sys
from pathlib import Path

from .main import app
from .settings import settings

# Ensure repo root is importable so we can access Auth service app
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from services.auth.app.main import app as auth_app


def mint_token(user_id: Optional[uuid.UUID] = None, is_active: bool = True, expires_in: int = 3600) -> str:
    """Create a signed JWT for tests compatible with get_current_user()."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id or uuid.uuid4()),
        "is_active": is_active,
        "iss": settings.JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def unique_email(prefix: str = "qa.inventory") -> str:
    return f"{prefix}.{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture(scope="session")
def auth_ctx() -> dict:
    """Create a real user in the shared database via Auth service."""
    with TestClient(auth_app) as ac:
        email = unique_email()
        password = "Admin123!__"
        r = ac.post("/auth/register", json={"email": email, "password": password})
        assert r.status_code == 201, r.text
        l = ac.post("/auth/login", json={"email": email, "password": password})
        assert l.status_code == 200, l.text
        auth_token = l.json()["payload"]["access_token"]
        # Retrieve the UUID from /user/me
        me = ac.get("/user/me", headers={"Authorization": f"Bearer {auth_token}"})
        assert me.status_code == 200, me.text
        me_payload = me.json()["payload"]
        user_id_str = me_payload.get("id")
        assert user_id_str, "Auth /user/me did not return id"
        # Inventory expects JWT sub to be a UUID string; mint a local token with that UUID
        inventory_token = mint_token(user_id=uuid.UUID(user_id_str))
        return {"token": inventory_token, "user_id": user_id_str, "email": email}


@pytest.fixture(scope="session")
def admin_ctx() -> dict:
    """Create an admin user for admin-only operations."""
    with TestClient(auth_app) as ac:
        email = unique_email("admin")
        password = "Admin123!__"
        r = ac.post("/auth/register", json={"email": email, "password": password})
        assert r.status_code == 201, r.text
        l = ac.post("/auth/login", json={"email": email, "password": password})
        assert l.status_code == 200, l.text
        auth_token = l.json()["payload"]["access_token"]
        me = ac.get("/user/me", headers={"Authorization": f"Bearer {auth_token}"})
        assert me.status_code == 200, me.text
        me_payload = me.json()["payload"]
        user_id_str = me_payload.get("id")
        admin_token = mint_token(user_id=uuid.UUID(user_id_str))
        return {"token": admin_token, "user_id": user_id_str, "email": email}


def test_health_endpoint(client: TestClient):
    """Test health endpoint returns proper status."""
    r = client.get("/inventory/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("status") == "ok"
    assert body.get("db") in {"up", "down"}


def test_landing_page_public_access(client: TestClient):
    """Test that landing pages are publicly accessible."""
    # Root landing page
    r = client.get("/")
    assert r.status_code == 200, r.text
    assert "text/html" in r.headers.get("content-type", "")
    
    # Prefixed landing page
    r2 = client.get("/inventory")
    assert r2.status_code == 200, r2.text
    assert "text/html" in r2.headers.get("content-type", "")


def test_products_require_auth(client: TestClient):
    """Test that product endpoints require authentication."""
    r = client.get("/api/products")
    assert r.status_code in (401, 403), r.text


def test_product_categories_list(client: TestClient, auth_ctx: dict):
    """Test product categories listing."""
    r = client.get("/api/products/categories/list", headers=auth_headers(auth_ctx["token"]))
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, dict)
    assert "product_types" in data
    assert "categories" in data
    assert "rarities" in data
    assert "acquisition_methods" in data


def test_product_crud_flow(client: TestClient, admin_ctx: dict):
    """Test complete product CRUD operations."""
    # Create product
    create_data = {
        "name": "QA Test Hair Color",
        "description": "Test hair color for QA",
        "product_type": "appearance",
        "category": "hair_color",
        "rarity": "common",
        "price_usd": 5.99,
        "acquisition_method": "purchase",
        "status": "active",
        "attributes": {"color_code": "#FF5733"},
        "tags": ["hair", "color", "test"]
    }
    
    create = client.post("/api/products", headers=auth_headers(admin_ctx["token"]), json=create_data)
    assert create.status_code == 201, create.text
    cj = create.json()
    payload = cj.get("payload", cj)
    product_id = payload["id"]
    assert payload["name"] == "QA Test Hair Color"
    
    # Get product
    get_one = client.get(f"/api/products/{product_id}", headers=auth_headers(admin_ctx["token"]))
    assert get_one.status_code == 200, get_one.text
    gj = get_one.json()
    gpayload = gj.get("payload", gj)
    assert gpayload["id"] == product_id
    assert gpayload["attributes"]["color_code"] == "#FF5733"
    
    # List products
    lst = client.get("/api/products", headers=auth_headers(admin_ctx["token"]))
    assert lst.status_code == 200, lst.text
    lj = lst.json()
    lpayload = lj if isinstance(lj, list) else lj.get("payload", lj)
    assert isinstance(lpayload, list)
    assert any(p["id"] == product_id for p in lpayload)
    
    # Update product
    update_data = {"name": "QA Test Hair Color Updated", "price_usd": 7.99}
    patch = client.patch(f"/api/products/{product_id}", headers=auth_headers(admin_ctx["token"]), json=update_data)
    assert patch.status_code == 200, patch.text
    pj = patch.json()
    ppayload = pj.get("payload", pj)
    assert ppayload["name"] == "QA Test Hair Color Updated"
    assert ppayload["price_usd"] == 7.99
    
    # Delete product
    dele = client.delete(f"/api/products/{product_id}", headers=auth_headers(admin_ctx["token"]))
    assert dele.status_code == 204, dele.text


def test_inventory_management_flow(client: TestClient, auth_ctx: dict, admin_ctx: dict):
    """Test user inventory management operations."""
    # First create a product to work with
    product_data = {
        "name": "QA Inventory Item",
        "product_type": "clothing",
        "category": "tops",
        "rarity": "common",
        "acquisition_method": "gift",
        "status": "active"
    }
    
    create_product = client.post("/api/products", headers=auth_headers(admin_ctx["token"]), json=product_data)
    assert create_product.status_code == 201, create_product.text
    product_id = create_product.json().get("payload", create_product.json())["id"]
    
    # Grant product to user (admin operation)
    grant = client.post(
        f"/api/inventory/grant/{auth_ctx['user_id']}/{product_id}",
        headers=auth_headers(admin_ctx["token"])
    )
    assert grant.status_code == 201, grant.text
    gj = grant.json()
    inventory_id = gj.get("payload", gj)["id"]
    
    # List user inventory
    lst = client.get("/api/inventory", headers=auth_headers(auth_ctx["token"]))
    assert lst.status_code == 200, lst.text
    lj = lst.json()
    lpayload = lj if isinstance(lj, list) else lj.get("payload", lj)
    assert isinstance(lpayload, list)
    assert any(item["id"] == inventory_id for item in lpayload)
    
    # Get specific inventory item
    get_item = client.get(f"/api/inventory/{inventory_id}", headers=auth_headers(auth_ctx["token"]))
    assert get_item.status_code == 200, get_item.text
    gij = get_item.json()
    gipayload = gij.get("payload", gij)
    assert gipayload["id"] == inventory_id
    assert gipayload["product_id"] == product_id
    
    # Update inventory item (equip)
    update = client.patch(
        f"/api/inventory/{inventory_id}",
        headers=auth_headers(auth_ctx["token"]),
        json={"is_equipped": True}
    )
    assert update.status_code == 200, update.text
    uj = update.json()
    upayload = uj.get("payload", uj)
    assert upayload["is_equipped"] is True
    
    # Clean up - remove from inventory (admin operation)
    remove = client.delete(f"/api/inventory/{inventory_id}", headers=auth_headers(admin_ctx["token"]))
    assert remove.status_code == 204, remove.text


def test_bundle_management_flow(client: TestClient, admin_ctx: dict):
    """Test product bundle creation and management."""
    # Create products for bundle
    product_ids = []
    for i in range(2):
        product_data = {
            "name": f"QA Bundle Item {i+1}",
            "product_type": "clothing",
            "category": "tops",
            "rarity": "common",
            "acquisition_method": "purchase",
            "status": "active",
            "price_usd": 10.0
        }
        create = client.post("/api/products", headers=auth_headers(admin_ctx["token"]), json=product_data)
        assert create.status_code == 201, create.text
        product_ids.append(create.json().get("payload", create.json())["id"])
    
    # Create bundle
    bundle_data = {
        "name": "QA Test Bundle",
        "description": "Test bundle for QA",
        "price_usd": 15.0,
        "discount_percentage": 25.0,
        "product_ids": product_ids,
        "tags": ["test", "bundle"]
    }
    
    create_bundle = client.post("/api/bundles", headers=auth_headers(admin_ctx["token"]), json=bundle_data)
    assert create_bundle.status_code == 201, create_bundle.text
    cj = create_bundle.json()
    bundle_id = cj.get("payload", cj)["id"]
    
    # Get bundle
    get_bundle = client.get(f"/api/bundles/{bundle_id}", headers=auth_headers(admin_ctx["token"]))
    assert get_bundle.status_code == 200, get_bundle.text
    gj = get_bundle.json()
    gpayload = gj.get("payload", gj)
    assert gpayload["name"] == "QA Test Bundle"
    assert len(gpayload["bundle_items"]) == 2
    
    # List bundles
    list_bundles = client.get("/api/bundles", headers=auth_headers(admin_ctx["token"]))
    assert list_bundles.status_code == 200, list_bundles.text
    lj = list_bundles.json()
    lpayload = lj if isinstance(lj, list) else lj.get("payload", lj)
    assert any(b["id"] == bundle_id for b in lpayload)
    
    # Update bundle
    update_bundle = client.patch(
        f"/api/bundles/{bundle_id}",
        headers=auth_headers(admin_ctx["token"]),
        json={"name": "QA Test Bundle Updated", "price_usd": 18.0}
    )
    assert update_bundle.status_code == 200, update_bundle.text
    uj = update_bundle.json()
    upayload = uj.get("payload", uj)
    assert upayload["name"] == "QA Test Bundle Updated"
    
    # Delete bundle
    delete_bundle = client.delete(f"/api/bundles/{bundle_id}", headers=auth_headers(admin_ctx["token"]))
    assert delete_bundle.status_code == 204, delete_bundle.text


def test_purchase_product_flow(client: TestClient, auth_ctx: dict, admin_ctx: dict):
    """Test purchasing individual products."""
    # Create purchasable product
    product_data = {
        "name": "QA Purchasable Item",
        "product_type": "accessories",
        "category": "jewelry",
        "rarity": "rare",
        "price_usd": 12.99,
        "acquisition_method": "purchase",
        "status": "active"
    }
    
    create_product = client.post("/api/products", headers=auth_headers(admin_ctx["token"]), json=product_data)
    assert create_product.status_code == 201, create_product.text
    product_id = create_product.json().get("payload", create_product.json())["id"]
    
    # Purchase product
    purchase = client.post(
        f"/api/purchases/product/{product_id}",
        headers=auth_headers(auth_ctx["token"]),
        json={"payment_method": "stripe"}
    )
    assert purchase.status_code == 201, purchase.text
    pj = purchase.json()
    ppayload = pj.get("payload", pj)
    purchase_id = ppayload["id"]
    assert ppayload["status"] == "completed"
    assert ppayload["amount_usd"] == 12.99
    
    # Verify product was added to inventory
    inventory = client.get("/api/inventory", headers=auth_headers(auth_ctx["token"]))
    assert inventory.status_code == 200, inventory.text
    inv_items = inventory.json()
    inv_payload = inv_items if isinstance(inv_items, list) else inv_items.get("payload", inv_items)
    assert any(item["product_id"] == product_id for item in inv_payload)
    
    # Get purchase details
    get_purchase = client.get(f"/api/purchases/{purchase_id}", headers=auth_headers(auth_ctx["token"]))
    assert get_purchase.status_code == 200, get_purchase.text
    gpj = get_purchase.json()
    gppayload = gpj.get("payload", gpj)
    assert gppayload["id"] == purchase_id
    
    # List purchases
    list_purchases = client.get("/api/purchases", headers=auth_headers(auth_ctx["token"]))
    assert list_purchases.status_code == 200, list_purchases.text
    lpj = list_purchases.json()
    lppayload = lpj if isinstance(lpj, list) else lpj.get("payload", lpj)
    assert any(p["id"] == purchase_id for p in lppayload)


def test_purchase_bundle_flow(client: TestClient, auth_ctx: dict, admin_ctx: dict):
    """Test purchasing product bundles."""
    # Create products for bundle
    product_ids = []
    for i in range(2):
        product_data = {
            "name": f"QA Bundle Purchase Item {i+1}",
            "product_type": "clothing",
            "category": "bottoms",
            "rarity": "uncommon",
            "price_usd": 8.0,
            "acquisition_method": "purchase",
            "status": "active"
        }
        create = client.post("/api/products", headers=auth_headers(admin_ctx["token"]), json=product_data)
        assert create.status_code == 201, create.text
        product_ids.append(create.json().get("payload", create.json())["id"])
    
    # Create bundle
    bundle_data = {
        "name": "QA Purchase Bundle",
        "description": "Bundle for purchase testing",
        "price_usd": 12.0,
        "product_ids": product_ids
    }
    
    create_bundle = client.post("/api/bundles", headers=auth_headers(admin_ctx["token"]), json=bundle_data)
    assert create_bundle.status_code == 201, create_bundle.text
    bundle_id = create_bundle.json().get("payload", create_bundle.json())["id"]
    
    # Purchase bundle
    purchase_bundle = client.post(
        f"/api/purchases/bundle/{bundle_id}",
        headers=auth_headers(auth_ctx["token"])
    )
    assert purchase_bundle.status_code == 201, purchase_bundle.text
    pj = purchase_bundle.json()
    ppayload = pj.get("payload", pj)
    purchase_id = ppayload["id"]
    assert ppayload["status"] == "completed"
    assert ppayload["amount_usd"] == 12.0
    
    # Verify all bundle products were added to inventory
    inventory = client.get("/api/inventory", headers=auth_headers(auth_ctx["token"]))
    assert inventory.status_code == 200, inventory.text
    inv_items = inventory.json()
    inv_payload = inv_items if isinstance(inv_items, list) else inv_items.get("payload", inv_items)
    
    for product_id in product_ids:
        assert any(item["product_id"] == product_id for item in inv_payload)


def test_refund_flow(client: TestClient, auth_ctx: dict, admin_ctx: dict):
    """Test purchase refund processing."""
    # Create and purchase a product
    product_data = {
        "name": "QA Refund Item",
        "product_type": "consumable",
        "category": "gift_box",
        "rarity": "common",
        "price_usd": 5.0,
        "acquisition_method": "purchase",
        "status": "active"
    }
    
    create_product = client.post("/api/products", headers=auth_headers(admin_ctx["token"]), json=product_data)
    assert create_product.status_code == 201, create_product.text
    product_id = create_product.json().get("payload", create_product.json())["id"]
    
    # Purchase product
    purchase = client.post(f"/api/purchases/product/{product_id}", headers=auth_headers(auth_ctx["token"]))
    assert purchase.status_code == 201, purchase.text
    purchase_id = purchase.json().get("payload", purchase.json())["id"]
    
    # Verify product is in inventory
    inventory_before = client.get("/api/inventory", headers=auth_headers(auth_ctx["token"]))
    inv_before = inventory_before.json()
    inv_before_payload = inv_before if isinstance(inv_before, list) else inv_before.get("payload", inv_before)
    assert any(item["product_id"] == product_id for item in inv_before_payload)
    
    # Request refund
    refund = client.post(f"/api/purchases/{purchase_id}/refund", headers=auth_headers(auth_ctx["token"]))
    assert refund.status_code == 200, refund.text
    rj = refund.json()
    rpayload = rj.get("payload", rj)
    assert rpayload["status"] == "refunded"
    
    # Verify product was removed from inventory
    inventory_after = client.get("/api/inventory", headers=auth_headers(auth_ctx["token"]))
    inv_after = inventory_after.json()
    inv_after_payload = inv_after if isinstance(inv_after, list) else inv_after.get("payload", inv_after)
    assert not any(item["product_id"] == product_id for item in inv_after_payload)


def test_edge_cases_and_validation(client: TestClient, auth_ctx: dict, admin_ctx: dict):
    """Test edge cases and validation scenarios."""
    # Test purchasing non-existent product
    fake_product_id = str(uuid.uuid4())
    purchase_fake = client.post(f"/api/purchases/product/{fake_product_id}", headers=auth_headers(auth_ctx["token"]))
    assert purchase_fake.status_code == 404, purchase_fake.text
    
    # Test duplicate purchase prevention
    product_data = {
        "name": "QA Duplicate Test",
        "product_type": "appearance",
        "category": "eye_color",
        "rarity": "common",
        "price_usd": 3.0,
        "acquisition_method": "purchase",
        "status": "active"
    }
    
    create_product = client.post("/api/products", headers=auth_headers(admin_ctx["token"]), json=product_data)
    product_id = create_product.json().get("payload", create_product.json())["id"]
    
    # First purchase should succeed
    purchase1 = client.post(f"/api/purchases/product/{product_id}", headers=auth_headers(auth_ctx["token"]))
    assert purchase1.status_code == 201, purchase1.text
    
    # Second purchase should fail (duplicate)
    purchase2 = client.post(f"/api/purchases/product/{product_id}", headers=auth_headers(auth_ctx["token"]))
    assert purchase2.status_code == 409, purchase2.text  # Conflict
    
    # Test purchasing inactive product
    inactive_product_data = {
        "name": "QA Inactive Product",
        "product_type": "clothing",
        "category": "shoes",
        "rarity": "common",
        "price_usd": 15.0,
        "acquisition_method": "purchase",
        "status": "disabled"
    }
    
    create_inactive = client.post("/api/products", headers=auth_headers(admin_ctx["token"]), json=inactive_product_data)
    inactive_id = create_inactive.json().get("payload", create_inactive.json())["id"]
    
    purchase_inactive = client.post(f"/api/purchases/product/{inactive_id}", headers=auth_headers(auth_ctx["token"]))
    assert purchase_inactive.status_code == 400, purchase_inactive.text
    
    # Test invalid refund (non-existent purchase)
    fake_purchase_id = str(uuid.uuid4())
    refund_fake = client.post(f"/api/purchases/{fake_purchase_id}/refund", headers=auth_headers(auth_ctx["token"]))
    assert refund_fake.status_code == 404, refund_fake.text


def test_authentication_and_authorization(client: TestClient):
    """Test authentication and authorization requirements."""
    # Test unauthenticated access
    endpoints_requiring_auth = [
        "/api/products",
        "/api/inventory",
        "/api/bundles",
        "/api/purchases"
    ]
    
    for endpoint in endpoints_requiring_auth:
        r = client.get(endpoint)
        assert r.status_code in (401, 403), f"Endpoint {endpoint} should require auth"
    
    # Test invalid token
    invalid_token = "invalid.jwt.token"
    for endpoint in endpoints_requiring_auth:
        r = client.get(endpoint, headers={"Authorization": f"Bearer {invalid_token}"})
        assert r.status_code in (401, 403), f"Endpoint {endpoint} should reject invalid token"


def test_inventory_filtering_and_pagination(client: TestClient, auth_ctx: dict, admin_ctx: dict):
    """Test inventory filtering and pagination features."""
    # Create multiple products and add to inventory
    product_ids = []
    for i in range(3):
        product_data = {
            "name": f"QA Filter Item {i+1}",
            "product_type": "clothing",
            "category": "tops",
            "rarity": "common",
            "acquisition_method": "gift",
            "status": "active"
        }
        create = client.post("/api/products", headers=auth_headers(admin_ctx["token"]), json=product_data)
        product_id = create.json().get("payload", create.json())["id"]
        product_ids.append(product_id)
        
        # Grant to user
        client.post(f"/api/inventory/grant/{auth_ctx['user_id']}/{product_id}", headers=auth_headers(admin_ctx["token"]))
    
    # Test pagination
    paginated = client.get("/api/inventory?limit=2&offset=0", headers=auth_headers(auth_ctx["token"]))
    assert paginated.status_code == 200, paginated.text
    pag_items = paginated.json()
    pag_payload = pag_items if isinstance(pag_items, list) else pag_items.get("payload", pag_items)
    assert len(pag_payload) <= 2
    
    # Test equipped filter (equip one item first)
    if product_ids:
        # Get inventory item ID
        inventory = client.get("/api/inventory", headers=auth_headers(auth_ctx["token"]))
        inv_items = inventory.json()
        inv_payload = inv_items if isinstance(inv_items, list) else inv_items.get("payload", inv_items)
        
        if inv_payload:
            inventory_id = inv_payload[0]["id"]
            # Equip item
            client.patch(f"/api/inventory/{inventory_id}", headers=auth_headers(auth_ctx["token"]), json={"is_equipped": True})
            
            # Filter equipped items
            equipped = client.get("/api/inventory?is_equipped=true", headers=auth_headers(auth_ctx["token"]))
            assert equipped.status_code == 200, equipped.text
            eq_items = equipped.json()
            eq_payload = eq_items if isinstance(eq_items, list) else eq_items.get("payload", eq_items)
            assert all(item["is_equipped"] for item in eq_payload)