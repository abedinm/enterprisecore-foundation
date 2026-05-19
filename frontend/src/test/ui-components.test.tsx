/**
 * Rendering tests for the primitive UI building blocks.
 * These guard against accidental class/attribute regressions.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";


describe("Button", () => {
  it("renders children and fires onClick", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Press me</Button>);
    const btn = screen.getByRole("button", { name: /press me/i });
    await userEvent.click(btn);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("applies the danger variant class", () => {
    render(<Button variant="danger">Delete</Button>);
    const btn = screen.getByRole("button", { name: /delete/i });
    expect(btn.className).toMatch(/rose-600/);
  });

  it("respects the disabled prop", () => {
    const onClick = vi.fn();
    render(<Button disabled onClick={onClick}>Nope</Button>);
    const btn = screen.getByRole("button");
    fireEvent.click(btn);
    expect(onClick).not.toHaveBeenCalled();
  });
});


describe("Badge", () => {
  it("renders with the given variant", () => {
    render(<Badge variant="success">OK</Badge>);
    const el = screen.getByText("OK");
    expect(el.className).toMatch(/emerald/);
  });
});


describe("Input", () => {
  it("forwards value and onChange", async () => {
    const Wrapper = () => {
      const [v, setV] = (require("react") as typeof import("react")).useState("");
      return (
        <Input
          aria-label="email"
          value={v}
          onChange={(e) => setV(e.target.value)}
        />
      );
    };
    render(<Wrapper />);
    const inp = screen.getByLabelText("email") as HTMLInputElement;
    await userEvent.type(inp, "hi@x.io");
    expect(inp.value).toBe("hi@x.io");
  });
});


describe("Card", () => {
  it("composes header/title/content", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Section</CardTitle>
        </CardHeader>
        <CardContent>Body text</CardContent>
      </Card>
    );
    expect(screen.getByText("Section")).toBeInTheDocument();
    expect(screen.getByText("Body text")).toBeInTheDocument();
  });
});
