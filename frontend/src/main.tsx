import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { TournamentProvider } from "./store";
import { RefreshProvider } from "./refresh";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <TournamentProvider>
        <RefreshProvider>
          <App />
        </RefreshProvider>
      </TournamentProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
