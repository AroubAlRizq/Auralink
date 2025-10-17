import { NavLink } from "react-router-dom";

export default function Navbar() {
  return (
    <header className="header-bar shadow-sm">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
        <div className="text-xl font-semibold tracking-wide">Auralink</div>
        <nav className="flex gap-4">
          <NavLink to="/" className="hover:underline">Dashboard</NavLink>
          <NavLink to="/timeline" className="hover:underline">Timeline</NavLink>
          <NavLink to="/chat" className="hover:underline">Chat</NavLink>
          <NavLink to="/analytics" className="hover:underline">Analytics</NavLink>
        </nav>
      </div>
    </header>
  );
}