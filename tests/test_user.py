import pytest
from app.services.drivers import create_driver, get_driver_by_id, update_driver
from app.services.users import create_user, get_user_by_id, update_user


@pytest.mark.asyncio
async def test_create_user_success():
    user_data = {
        "email": "test@example.com",
        "name": "Test User",
        "password": "securepassword",
    }
    user = await create_user(user_data)
    assert user.email == user_data["email"]


@pytest.mark.asyncio
async def test_create_user_existing_email():
    user_data = {
        "email": "existing@example.com",
        "name": "Existing User",
        "password": "securepassword",
    }
    await create_user(user_data)
    with pytest.raises(ValueError):
        await create_user(user_data)


@pytest.mark.asyncio
async def test_create_user_invalid_data():
    user_data = {"email": "invalid-email", "name": "", "password": "short"}
    with pytest.raises(ValueError):
        await create_user(user_data)


@pytest.mark.asyncio
async def test_create_driver_success():
    driver_data = {
        "email": "driver@example.com",
        "name": "Test Driver",
        "license_number": "D1234567",
    }
    driver = await create_driver(driver_data)
    assert driver.email == driver_data["email"]


@pytest.mark.asyncio
async def test_create_driver_existing_email():
    driver_data = {
        "email": "existingdriver@example.com",
        "name": "Existing Driver",
        "license_number": "D1234567",
    }
    await create_driver(driver_data)
    with pytest.raises(ValueError):
        await create_driver(driver_data)


@pytest.mark.asyncio
async def test_create_driver_invalid_data():
    driver_data = {"email": "invalid-email", "name": "", "license_number": ""}
    with pytest.raises(ValueError):
        await create_driver(driver_data)


@pytest.mark.asyncio
async def test_get_user_by_id_success():
    user = await create_user(
        {
            "email": "fetch@example.com",
            "name": "Fetch User",
            "password": "securepassword",
        }
    )
    fetched_user = await get_user_by_id(user.id)
    assert fetched_user.id == user.id


@pytest.mark.asyncio
async def test_get_user_by_id_non_existent():
    with pytest.raises(ValueError):
        await get_user_by_id(9999)


@pytest.mark.asyncio
async def test_get_driver_by_id_success():
    driver = await create_driver(
        {
            "email": "fetchdriver@example.com",
            "name": "Fetch Driver",
            "license_number": "D1234567",
        }
    )
    fetched_driver = await get_driver_by_id(driver.id)
    assert fetched_driver.id == driver.id


@pytest.mark.asyncio
async def test_get_driver_by_id_non_existent():
    with pytest.raises(ValueError):
        await get_driver_by_id(9999)


@pytest.mark.asyncio
async def test_update_user_success():
    user = await create_user(
        {
            "email": "update@example.com",
            "name": "Update User",
            "password": "securepassword",
        }
    )
    updated_data = {"name": "Updated User"}
    updated_user = await update_user(user.id, updated_data)
    assert updated_user.name == updated_data["name"]


@pytest.mark.asyncio
async def test_update_user_invalid_data():
    user = await create_user(
        {
            "email": "updateinvalid@example.com",
            "name": "Update Invalid User",
            "password": "securepassword",
        }
    )
    updated_data = {"email": "invalid-email"}
    with pytest.raises(ValueError):
        await update_user(user.id, updated_data)


@pytest.mark.asyncio
async def test_update_driver_success():
    driver = await create_driver(
        {
            "email": "updatedriver@example.com",
            "name": "Update Driver",
            "license_number": "D1234567",
        }
    )
    updated_data = {"name": "Updated Driver"}
    updated_driver = await update_driver(driver.id, updated_data)
    assert updated_driver.name == updated_data["name"]


@pytest.mark.asyncio
async def test_update_driver_invalid_data():
    driver = await create_driver(
        {
            "email": "updateinvaliddriver@example.com",
            "name": "Update Invalid Driver",
            "license_number": "D1234567",
        }
    )
    updated_data = {"license_number": ""}
    with pytest.raises(ValueError):
        await update_driver(driver.id, updated_data)
