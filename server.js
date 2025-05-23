const express = require("express");
const fs = require("fs");
const path = require("path");
const cors = require("cors");
const bodyParser = require("body-parser");

const app = express();
const port = 8000;

// Путь к файлу с "базой данных"
const DB_PATH = path.join(__dirname, 'db.json');

// Загружаем пользователей из файла
let users = [];

function loadUsers() {
  try {
    const data = fs.readFileSync(DB_PATH, 'utf-8');
    const json = JSON.parse(data);
    users = json.users || [];
  } catch (err) {
    console.error("Ошибка при загрузке пользователей:", err);
    users = [];
  }
}

function saveUsers() {
  try {
    const data = JSON.stringify({ users }, null, 2);
    fs.writeFileSync(DB_PATH, data, 'utf-8');
  } catch (err) {
    console.error("Ошибка при сохранении пользователей:", err);
  }
}

// Загрузка пользователей при запуске
loadUsers();


// Разрешаем запросы с localhost:3000
app.use(
  cors({
    origin: "http://localhost:3000", // Разрешаем запросы только с этого источника
    credentials: true, // Разрешаем куки
  })
);

/*app.use(cors());*/

// Парсим JSON-тело запроса
app.use(bodyParser.json());

// Middleware для добавления задержки
app.use((req, res, next) => {
  const delay = 500;
  setTimeout(() => {
    next();
  }, delay);
});

// Путь к видеофайлу
const videoPath = path.join(__dirname, "MengerSponge.mp4");

// Отдаём видео клиенту
app.get("/video", (req, res) => {
  if (fs.existsSync(videoPath)) {
    res.setHeader("Cache-Control", "public, max-age=31536000"); // кэшировать на год
    res.sendFile(videoPath);
  } else {
    res.status(404).send("Видео ещё не готово.");
  }
});

// Маршрут для логина
app.post("/login", (req, res) => {
  console.log("/login");
  const { email, password } = req.body;
  console.log("Вход:", email, password);

  // Ищем пользователя
  const user = users.find((u) => u.email === email && u.password === password);

  if (user) {
    res.status(200).json({
      token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", // фейковый токен
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role,
      },
    });
  } else {
    res.status(401).json({ message: "Неверный логин или пароль!" });
  }
});

app.post("/register", (req, res) => {
  const { name, email, password } = req.body;

  if (!name || !email || !password) {
    return res.status(400).json({ message: "Все поля обязательны" });
  }

  const userExists = users.find((user) => user.email === email);
  if (userExists) {
    return res.status(403).json({ message: "Пользователь уже существует" });
  }

  const newUser = {
    id: users.length + 1,
    name,
    email,
    password, // В продакшене обязательно хешируй!
    role: "user",
  };

  users.push(newUser);
  saveUsers(); // сохраняем в файл

  const { password: _, ...userWithoutPassword } = newUser;

  res.status(201).json({
    message: "Пользователь зарегистрирован",
    user: userWithoutPassword,
  });
});


// Статический сервер для клиента
app.use(express.static("public"));

// Отдаём React фронт
//app.use(express.static(path.join(__dirname, '../client/build')));

// Обработка всех остальных маршрутов — возвращаем index.html
/*app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../client/build', 'index.html'));
});*/

app.listen(port, () => {
  console.log(`Сервер запущен: http://localhost:${port}`);
});