from app.database.connection import engine
from app.models.base import Base

# import all models
from app.models.user import *
from app.models.product import *
from app.models.cart import *
from app.models.order import *

Base.metadata.create_all(bind=engine)

print("Database created successfully!")