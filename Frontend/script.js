const form = document.getElementById("recipeForm");
const msg = document.getElementById("msg");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const data = {
    title: document.getElementById("title").value,
    ingredients: document.getElementById("ingredients").value,
    instructions: document.getElementById("instructions").value
  };

  try {
    const response = await fetch("http://localhost/uvareno/backend/add_recipe.php", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });

    const result = await response.json();
    msg.textContent = result.message;
    form.reset();
  } catch (error) {
    msg.textContent = "Chyba při odesílání dat.";
  }
});
