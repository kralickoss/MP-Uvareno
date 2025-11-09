<?php
$servername = "localhost";
$username = "root";
$password = "";
$dbname = "uvareno";

$conn = new mysqli($servername, $username, $password, $dbname);

if ($conn->connect_error) {
    die("Připojení k databázi selhalo: " . $conn->connect_error);
}
?>
