from database import engine

try:
    with engine.connect() as connection:
        print("DATABASE CONNECTION SUCCESSFUL!")
except Exception as e:
    print("DATABASE CONNECTION FAILED!")
    print(e)