import React from "react";
import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import ChatBubble from "./components/ChatBubble";
import Dashboard from "./pages/Dashboard";
import Timeline from "./pages/Timeline";
import Chat from "./pages/Chat";
import Analytics from "./pages/Analytics";

export default function App() {
  return (
    <div className="flex flex-col min-h-screen bg-white text-gray-800">
      {/* Navbar */}
      <Navbar />

      {/* Main Page Routes */}
      <main className="flex-grow">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/timeline" element={<Timeline />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/analytics" element={<Analytics />} />
        </Routes>
      </main>

      {/* Floating Chat Icon */}
      <ChatBubble />

      {/* Footer */}
      <Footer />
    </div>
  );
}
