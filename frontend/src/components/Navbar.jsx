import { NavLink } from "react-router-dom";
import logo from "../assets/auralink-logo.png";

export default function Navbar() {
  const base =
    "px-3 py-1.5 rounded-xl text-sm font-medium transition hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-white/30";
  const active = "bg-white/15 text-white";

  return (
    <header className="header-bar shadow-sm">
      <div className="max-w-6xl mx-auto px-6 flex items-center justify-between h-16 md:h-20">
        {/* ---------- Logo (enlarged + vertically centered) ---------- */}
        <NavLink to="/" className="flex items-center">
          <img
            src={logo}
            alt="Auralink Logo"
            className="h-20 md:h-24 w-auto "
            style={{
              transform: "scale(1.5)",
              transformOrigin: "left center",
              display: "block",
            }}
          />
        </NavLink>

        {/* ---------- Navigation ---------- */}
        <nav className="flex gap-3 md:gap-5 items-center">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `${base} ${isActive ? active : "text-white/90"}`
            }
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/timeline"
            className={({ isActive }) =>
              `${base} ${isActive ? active : "text-white/90"}`
            }
          >
            Timeline
          </NavLink>
          <NavLink
            to="/chat"
            className={({ isActive }) =>
              `${base} ${isActive ? active : "text-white/90"}`
            }
          >
            Chat
          </NavLink>
          <NavLink
            to="/analytics"
            className={({ isActive }) =>
              `${base} ${isActive ? active : "text-white/90"}`
            }
          >
            Analytics
          </NavLink>
        </nav>
      </div>
    </header>
  );
}