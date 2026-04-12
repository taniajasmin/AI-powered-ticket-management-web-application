function buildNav() {
    const user = getUser();
    if (!user) return;

    const role = user.role;
    const links = [
        { href: "/static/dashboard.html", label: "Dashboard", roles: ["admin", "customer"] },
        { href: "/static/tickets.html", label: "Tickets", roles: ["admin", "customer"] },
        { href: "/static/users.html", label: "Users", roles: ["admin"] },
        { href: "/static/customers.html", label: "Customers", roles: ["admin"] },
    ];

    const nav = document.getElementById("navLinks");
    nav.innerHTML = links
        .filter(l => l.roles.includes(role))
        .map(l => `<li><a href="${l.href}" class="${location.pathname.endsWith(l.href.split("/").pop()) ? "active" : ""}">${l.label}</a></li>`)
        .join("");

    const badge = document.getElementById("userBadge");
    badge.innerHTML = `${user.full_name} <span class="role">${user.role}</span> <a href="#" onclick="logout()" style="margin-left:8px;font-size:12px">Logout</a>`;
}

buildNav();
