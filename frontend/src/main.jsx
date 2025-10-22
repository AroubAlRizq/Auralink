import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import "./index.css";
import { MeetingProvider } from "./context/MeetingContext.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <MeetingProvider>
        <App />
      </MeetingProvider>
    </BrowserRouter>
  </React.StrictMode>
);