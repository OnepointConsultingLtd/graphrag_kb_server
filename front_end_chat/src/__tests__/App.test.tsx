import { test } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "../App";

test("App renders without crashing", () => {
  render(<App />);
  screen.debug();
  // Add your test assertions here
});
