<?php
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");
header("Access-Control-Allow-Methods: POST");

include "connect.php";

$data = json_decode(file_get_contents("php://input"), true);

if (!isset($data["title"]) || !isset($data["ingredients"]) || !isset($data["instructions"])) {
    echo json_encode(["message" => "Vyplň všechna pole."]);
    exit;
}

$title = $conn->real_escape_string($data["title"]);
$ingredients = $conn->real_escape_string($data["ingredients"]);
$instructions = $conn->real_escape_string($data["instructions"]);

$sql = "INSERT INTO recipes (title, ingredients, instructions) VALUES ('$title', '$ingredients', '$instructions')";

if ($conn->query($sql) === TRUE) {
    echo json_encode(["message" => "✅ Recept byl úspěšně uložen."]);
} else {
    echo json_encode(["message" => "❌ Chyba při ukládání receptu: " . $conn->error]);
}

$conn->close();
?>
