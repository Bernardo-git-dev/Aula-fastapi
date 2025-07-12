const api = "http://localhost:8000";

async function login() {
  const email = document.getElementById("email").value;
  const senha = document.getElementById("senha").value;

  const res = await fetch(`${api}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, senha }),
  });

  if (res.ok) {
    const data = await res.json();
    localStorage.setItem("token", data.access_token);
    window.location.href = "dashboard.html";
  } else {
    alert("Credenciais inválidas");
  }
}

async function register() {
  const name = document.getElementById("name").value;
  const email = document.getElementById("email").value;
  const idade = parseInt(document.getElementById("idade").value);
  const senha = document.getElementById("senha").value;

  const res = await fetch(`${api}/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, idade, senha }),
  });

  if (res.ok) {
    alert("Usuário cadastrado com sucesso!");
    window.location.href = "index.html";
  } else {
    const data = await res.json();
    alert(data.detail || "Erro ao registrar");
  }
}

async function loadUsers() {
  const token = localStorage.getItem("token");
  if (!token) return (window.location.href = "index.html");

  const res = await fetch(`${api}/users`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (res.ok) {
    const users = await res.json();
    const container = document.getElementById("usersContainer");
    container.innerHTML = "";

    users.forEach((user) => {
      container.innerHTML += `
        <div class="bg-white p-4 rounded shadow">
          <h3 class="text-xl font-bold">${user.name}</h3>
          <p><strong>Email:</strong> ${user.email}</p>
          <p><strong>Idade:</strong> ${user.idade}</p>
          <button onclick="deleteUser('${user._id}')" class="mt-2 bg-red-500 text-white px-3 py-1 rounded hover:bg-red-600">Deletar</button>
        </div>
      `;
    });
  } else {
    alert("Erro ao carregar usuários");
  }
}

async function deleteUser(id) {
  const token = localStorage.getItem("token");
  if (!confirm("Tem certeza que deseja deletar?")) return;

  const res = await fetch(`${api}/users/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (res.ok) {
    loadUsers();
  } else {
    alert("Erro ao deletar usuário");
  }
}

function logout() {
  localStorage.removeItem("token");
  window.location.href = "index.html";
}
