from flask import Flask, render_template, request, redirect, url_for, session
import requests

app = Flask(__name__)
app.secret_key = 'bba7e0cb777b1f6ce2830cdad5b2b9b2ef875d7814be3ed6'  # Cambia esto a una clave secreta real

RECIPES = {
    "Very Crude Gabagool": {
        "internal_id": "VERY_CRUDE_GABAGOOL",
        "output": 1,
        "materials": {
            "Crude Gabagool": 192
        }
    },
    "Enchanted Coal": {
        "internal_id": "ENCHANTED_COAL",
        "output": 1,
        "materials": {
            "Coal": 160
        }
    },
    "Enchanted Sulphur": {
        "internal_id": "ENCHANTED_SULPHUR",
        "output": 1,
        "materials": {
            "Sulphur": 160
        }
    },
    "Sulphuric Coal": {
        "internal_id": "SULPHURIC_COAL",
        "output": 4,
        "materials": {
            "Enchanted Coal": 16,
            "Enchanted Sulphur": 1
        }
    },
    "Fuel Gabagool": {
        "internal_id": "FUEL_GABAGOOL",
        "output": 8,
        "materials": {
            "Very Crude Gabagool": 1,
            "Sulphuric Coal": 8
        }
    },
    "Heavy Gabagool": {
        "internal_id": "HEAVY_GABAGOOL",
        "output": 1,
        "materials": {
            "Fuel Gabagool": 24,
            "Sulphuric Coal": 1
        }
    },
    "Hypergolic Gabagool": {
        "internal_id": "HYPERGOLIC_GABAGOOL",
        "output": 1,
        "materials": {
            "Heavy Gabagool": 12,
            "Sulphuric Coal": 1
        }
    },
    "Inferno Minion Fuel": {
        "internal_id": "INFERNO_HYPERGOLIC_CRUDE_GABAGOOL",
        "output": 1,
        "materials": {
            "Gabagool Distillate": 6,
            "Inferno Fuel Block": 2,
            "Hypergolic Gabagool": 1
        }
    }
}

ITEMS_NO_CRAFT = {
    "Gabagool Distillate": "CRUDE_GABAGOOL_DISTILLATE",
    "Inferno Fuel Block": "INFERNO_FUEL_BLOCK",
    "Coal": "COAL",
    "Sulphur": "SULPHUR_ORE",
    "Crude Gabagool": "CRUDE_GABAGOOL"
}

available_materials = {}

def fetch_bazaar_price(internal_id):
    try:
        uri = "https://api.hypixel.net/skyblock/bazaar"
        response = requests.get(uri)
        response.raise_for_status()
        data = response.json()
        if internal_id in data['products']:
            return data['products'][internal_id]['quick_status']['buyPrice']
        else:
            raise ValueError(f"No se encontró el precio para {internal_id}. Estableciendo el precio en 0.")
    except requests.RequestException as e:
        raise ValueError(f"Error de Conexión: {e}")

def decompose_materials(materials):
    decomposed = {}
    for material, quantity in materials.items():
        if material in RECIPES:
            output_quantity = RECIPES[material]["output"]
            components = RECIPES[material]["materials"]
            for component, amount in components.items():
                total_amount = (amount / output_quantity) * quantity
                if component in decomposed:
                    decomposed[component] += total_amount
                else:
                    decomposed[component] = total_amount
        else:
            if material in decomposed:
                decomposed[material] += quantity
            else:
                decomposed[material] = quantity
    return decomposed

def calculate_detailed_materials(recipe, quantity, available_materials):
    required_materials = {}
    price_total = 0
    output_qty = RECIPES[recipe]["output"]
    materials = RECIPES[recipe]["materials"]

    factor = quantity / output_qty

    for material, amount in materials.items():
        total_amount = amount * factor
        if material in available_materials:
            available_amount = available_materials[material]
            if available_amount >= total_amount:
                available_materials[material] -= total_amount
                total_amount = 0
            else:
                total_amount -= available_amount
                available_materials[material] = 0

        if material in RECIPES:
            sub_materials, sub_price = calculate_detailed_materials(material, total_amount, available_materials)
            for sub_material, sub_amount in sub_materials.items():
                if sub_material in required_materials:
                    required_materials[sub_material] += sub_amount
                else:
                    required_materials[sub_material] = sub_amount
            price_total += sub_price
        else:
            if material in required_materials:
                required_materials[material] += total_amount
            else:
                required_materials[material] = total_amount

            internal_id = ITEMS_NO_CRAFT.get(material, RECIPES.get(material, {}).get("internal_id", ""))
            price_per_unit = fetch_bazaar_price(internal_id)
            price_total += total_amount * price_per_unit

    return required_materials, price_total

def calculate_total_materials(recipe, quantity, available_materials):
    decomposed_materials = decompose_materials(available_materials)
    materials, price_total = calculate_detailed_materials(recipe, quantity, decomposed_materials)
    total_materials = {}

    for mat, qty in materials.items():
        if mat in total_materials:
            total_materials[mat] += qty
        else:
            total_materials[mat] = qty

    return total_materials, price_total

def format_quantity(quantity):
    return f"{quantity:.2f}".rstrip('0').rstrip('.') if quantity % 1 else str(int(quantity))

def format_price(price):
    if price >= 1_000_000_000:
        return f"{price / 1_000_000_000:.2f}b Coins"
    elif price >= 1_000_000:
        return f"{price / 1_000_000:.2f}m Coins"
    elif price >= 1_000:
        return f"{price / 1_000:.2f}k Coins"
    return f"{price:.2f} Coins"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/available", methods=["GET", "POST"])
def available():
    if request.method == "POST":
        for item in request.form:
            available_materials[item] = float(request.form.get(item, 0))
        return redirect(url_for("total_materials"))

    return render_template("available.html", materials=ITEMS_NO_CRAFT.keys() | RECIPES.keys(), available_materials=available_materials)

@app.route("/calculate", methods=["POST"])
def calculate():
    quantity = int(request.form["quantity"])
    session['quantity'] = quantity  # Guardar la cantidad en la sesión
    available_materials_copy = available_materials.copy()
    required_materials, total_price = calculate_detailed_materials("Inferno Minion Fuel", quantity, available_materials_copy)
    
    materials_html = f"<h3 style='line-height:1.2em;'>Materiales necesarios (detallado):</h3>"
    materials_html += show_detailed_materials_html("Inferno Minion Fuel", quantity, available_materials_copy, 0)
    
    total_price_main = calculate_main_components_price(quantity)
    materials_html += f"<p style='font-size:18pt;'><strong>Precio total (♣):</strong> {format_price(total_price_main)}</p>"

    return render_template("result.html", materials_html=materials_html)

@app.route("/total", methods=["GET", "POST"])
def total_materials():
    # Verificar si hay una cantidad en el formulario o la sesión
    if request.method == "POST":
        quantity = int(request.form.get("quantity", session.get('quantity', 1)))
    else:
        quantity = int(session.get('quantity', 1))
    
    session['quantity'] = quantity  # Guardar la cantidad en la sesión

    available_materials_copy = available_materials.copy()
    total_materials, total_price = calculate_total_materials("Inferno Minion Fuel", quantity, available_materials_copy)

    materials_html = f"<h3 style='line-height:1.2em;'>Materiales necesarios totales:</h3>"
    for material, qty in total_materials.items():
        if material not in ["Gabagool Distillate", "Inferno Fuel Block", "Coal", "Sulphur", "Crude Gabagool"]:
            continue
        internal_id = ITEMS_NO_CRAFT.get(material, RECIPES.get(material, {}).get("internal_id", ""))
        price_per_unit = fetch_bazaar_price(internal_id)
        total_price_item = qty * price_per_unit if price_per_unit else 0
        price_string = f" (Precio: {format_price(total_price_item)})" if total_price_item else ""
        image_filename = f"{material.replace(' ', '_').lower()}.png"
        image_url = url_for('static', filename=f'images/materials/result/{image_filename}')
        materials_html += f"""
        <li class="material-item">
            <div class="material-info">
                <img src="{image_url}" alt="{material}" class="material-image">
                <p style='color:black; text-shadow: 1px 1px 2px white;'>{material}: {format_quantity(qty)}{price_string}</p>
            </div>
        </li>
        """
    
    materials_html += f"<p style='font-size:18pt;'><strong>Precio total estimado:</strong> {format_price(total_price)}</p>"

    materials_html += '''
    <form action="/available" method="get" class="total-form">
        <button type="submit" class="available-button">Ingresar Materiales Disponibles</button>
    </form>
    '''

    return render_template("result.html", materials_html=materials_html)

def show_detailed_materials_html(recipe, quantity, available_materials, indent=0, parent_id=""):
    output_qty = RECIPES[recipe]["output"]
    materials = RECIPES[recipe]["materials"]
    factor = quantity / output_qty
    materials_html = ""

    for material, amount in materials.items():
        total_amount = amount * factor
        if material in available_materials:
            available_amount = available_materials[material]
            if available_amount >= total_amount:
                available_materials[material] -= total_amount
                total_amount = 0
            else:
                total_amount -= available_amount
                available_materials[material] = 0

        internal_id = ITEMS_NO_CRAFT.get(material, RECIPES.get(material, {}).get("internal_id", ""))
        price_per_unit = fetch_bazaar_price(internal_id)
        total_price = total_amount * price_per_unit if price_per_unit else 0
        price_string = f" (Precio: {format_price(total_price)})" if total_price else ""

        # Generar la URL para la imagen del material
        image_filename = f"{material.replace(' ', '_').lower()}"
        if material in ["Enchanted Coal", "Enchanted Sulphur"]:
            image_filename += ".gif"
        else:
            image_filename += ".png"

        image_url = url_for('static', filename=f'images/materials/result/{image_filename}')
        
        material_id = f"{parent_id}-{material.replace(' ', '_')}" if parent_id else material.replace(' ', '_')

        materials_html += f"""
        <li class="material-item">
            <div class="material-info">
                <img src="{image_url}" alt="{material}" class="material-image">
                <p style='color:black; text-shadow: 1px 1px 2px white;'>{material}: {format_quantity(total_amount)}{price_string}</p>
            </div>
            {"<button class='expand-button' data-target='" + material_id + "'>Expandir</button>" if material in RECIPES else ""}
            <ul class='details hidden' id="{material_id}">
                {show_detailed_materials_html(material, total_amount, available_materials, indent + 1, material_id) if material in RECIPES else ""}
            </ul>
        </li>
        """

    return materials_html

def calculate_main_components_price(units):
    total_price_main = 0
    components = ["Gabagool Distillate", "Inferno Fuel Block", "Hypergolic Gabagool"]
    for component in components:
        internal_id = ITEMS_NO_CRAFT.get(component, RECIPES.get(component, {}).get("internal_id", ""))
        price_per_unit = fetch_bazaar_price(internal_id)
        total_price_component = units * price_per_unit if price_per_unit else 0
        total_price_main += total_price_component
    return total_price_main

if __name__ == "__main__":
    app.run(debug=True)
