from pymongo import MongoClient

client = MongoClient("mongodb+srv://Finalyear_project:Rick123@finalyearproject.iimirt2.mongodb.net/?retryWrites=true&w=majority")
db = client["Finalyearproject"]  # replace with actual DB name
