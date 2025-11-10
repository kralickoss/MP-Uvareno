from flask import Flask, jsonify, request
import mysql.connector

app = Flask(__name__)

# Připojení k databázi
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # doplň své heslo
    database="uvareno"
)

@app.route("/recipes")
def get_recipes():
    cursor = db.cursor(dictionary=True)
    category = request.args.get("category")

    if category and category != "všechny":
        cursor.execute("SELECT * FROM recepty WHERE kategorie = %s", (category,))
    else:
        cursor.execute("SELECT * FROM recepty")

    recipes = cursor.fetchall()
    cursor.close()
    return jsonify(recipes)

if __name__ == "__main__":
    app.run(debug=True)
