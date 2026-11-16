import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";
import "./components/AppTheme.css";
import "./components/AnalysisScreen.css";
import "./components/AnalysisDialogs.css";
import "./components/AnalysisActions.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
