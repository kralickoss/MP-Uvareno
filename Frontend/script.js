// Načtení receptů z backendu
async function loadRecipes() {
  const response = await fetch("http://localhost:5000/recipes");
  const data = await response.json();
  renderRecipes(data);
}

// Zobrazení receptů na stránce
function renderRecipes(recipes) {
  const container = document.getElementById("recipe-container");
  container.innerHTML = "";

  recipes.forEach((recipe) => {
    const card = document.createElement("div");
    card.classList.add("recipe-card");
    card.innerHTML = `
      <h3>${recipe.nazev}</h3>
      <p>${recipe.kategorie}</p>
    `;
    container.appendChild(card);
  });
}

// Filtrování podle kategorie
function filterCategory(category) {
  fetch(`http://localhost:5000/recipes?category=${category}`)
    .then((res) => res.json())
    .then((data) => renderRecipes(data));
}

// Spuštění po načtení stránky
document.addEventListener("DOMContentLoaded", loadRecipes);
