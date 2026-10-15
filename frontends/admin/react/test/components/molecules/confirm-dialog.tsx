import React from "react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { logOutOutline } from "ionicons/icons";

import { ConfirmDialog } from "../../../components/molecules";

describe("ConfirmDialogTest", () => {
    afterEach(() => {
        cleanup();
    });

    const renderDialog = (onConfirm = vi.fn(), onCancel = vi.fn()) =>
        render(
            <ConfirmDialog
                title="Log out of Colony Print?"
                message="You're signed in as admin."
                confirmLabel="Log out"
                icon={logOutOutline}
                onConfirm={onConfirm}
                onCancel={onCancel}
            />
        );

    test("test_render", () => {
        const { container } = renderDialog();
        const dialog = screen.getByRole("dialog", {
            name: "Log out of Colony Print?"
        });
        expect(dialog.getAttribute("aria-modal")).toBe("true");
        expect(
            document.getElementById(
                dialog.getAttribute("aria-describedby") as string
            )?.textContent
        ).toBe("You're signed in as admin.");
        expect(
            screen.getByRole("heading", { name: "Log out of Colony Print?" })
                .tagName
        ).toBe("H2");
        expect(
            Array.from(dialog.querySelectorAll("button")).map(
                (button) => button.textContent
            )
        ).toEqual(["Cancel", "Log out"]);
        expect(
            dialog
                .querySelector(".confirm-dialog-icon ion-icon")
                ?.getAttribute("icon")
        ).toBe(logOutOutline);

        // the dialog is rendered in the body of the page, out of the
        // element that renders it (e.g., the side bar that is moved)
        expect(container.querySelector(".confirm-dialog")).toBe(null);
        expect(dialog.parentElement?.className).toBe("confirm-dialog-overlay");
        expect(dialog.parentElement?.parentElement).toBe(document.body);
    });

    test("test_render_icon", () => {
        render(
            <ConfirmDialog
                title="Cancel the job?"
                message="The job is not printed."
                confirmLabel="Log out"
                onConfirm={vi.fn()}
                onCancel={vi.fn()}
            />
        );
        const dialog = screen.getByRole("dialog", { name: "Cancel the job?" });
        expect(dialog.querySelector("ion-icon")).toBe(null);
        expect(
            screen.getByRole("button", { name: "Log out" }).textContent
        ).toBe("Log out");
    });

    test("test_focus", () => {
        // the cancel action (the safe one) is focused once shown, and the
        // focus goes back to the element that had it once gone
        const opener = document.createElement("button");
        document.body.appendChild(opener);
        try {
            opener.focus();
            const { unmount } = renderDialog();
            expect(document.activeElement).toBe(
                screen.getByRole("button", { name: "Cancel" })
            );
            unmount();
            expect(document.activeElement).toBe(opener);
        } finally {
            opener.remove();
        }
    });

    test("test_focus_tab", () => {
        // the focus is kept in the actions of the dialog, as the page
        // behind it (e.g., the links of the side bar) can't be used
        const outside = document.createElement("button");
        document.body.appendChild(outside);
        try {
            renderDialog();
            const cancel = screen.getByRole("button", { name: "Cancel" });
            const confirm = screen.getByRole("button", { name: "Log out" });
            fireEvent.keyDown(document, { key: "Tab" });
            expect(document.activeElement).toBe(confirm);
            fireEvent.keyDown(document, { key: "Tab" });
            expect(document.activeElement).toBe(cancel);
            fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
            expect(document.activeElement).toBe(confirm);
            fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
            expect(document.activeElement).toBe(cancel);

            // the focus that was moved out of the dialog comes back to it
            outside.focus();
            const event = new KeyboardEvent("keydown", {
                key: "Tab",
                bubbles: true,
                cancelable: true
            });
            document.dispatchEvent(event);
            expect(event.defaultPrevented).toBe(true);
            expect(document.activeElement).toBe(cancel);

            // while the other keys keep their behavior
            const other = new KeyboardEvent("keydown", {
                key: "a",
                bubbles: true,
                cancelable: true
            });
            document.dispatchEvent(other);
            expect(other.defaultPrevented).toBe(false);
            expect(document.activeElement).toBe(cancel);
        } finally {
            outside.remove();
        }
    });

    test("test_confirm", () => {
        const onConfirm = vi.fn();
        const onCancel = vi.fn();
        renderDialog(onConfirm, onCancel);
        fireEvent.click(screen.getByRole("button", { name: "Log out" }));
        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onCancel).not.toHaveBeenCalled();
    });

    test("test_cancel", () => {
        const onConfirm = vi.fn();
        const onCancel = vi.fn();
        renderDialog(onConfirm, onCancel);

        // the dialog is cancelled by its button, by the escape key and
        // by a click out of it (on the overlay), never by one in it
        fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
        fireEvent.keyDown(document, { key: "Escape" });
        fireEvent.click(document.querySelector(".confirm-dialog-overlay")!);
        expect(onCancel).toHaveBeenCalledTimes(3);

        fireEvent.click(screen.getByRole("dialog"));
        fireEvent.click(screen.getByText("You're signed in as admin."));
        fireEvent.keyDown(document, { key: "Enter" });
        expect(onCancel).toHaveBeenCalledTimes(3);
        expect(onConfirm).not.toHaveBeenCalled();
    });

    test("test_cancel_changed", () => {
        // the escape key cancels with the handler of the last render, as
        // the components that render the dialog create a new one each time
        const first = vi.fn();
        const second = vi.fn();
        const { rerender, unmount } = renderDialog(vi.fn(), first);
        rerender(
            <ConfirmDialog
                title="Log out of Colony Print?"
                message="You're signed in as admin."
                confirmLabel="Log out"
                onConfirm={vi.fn()}
                onCancel={second}
            />
        );
        fireEvent.keyDown(document, { key: "Escape" });
        expect(first).not.toHaveBeenCalled();
        expect(second).toHaveBeenCalledTimes(1);

        // and is not handled anymore once the dialog is gone
        unmount();
        fireEvent.keyDown(document, { key: "Escape" });
        expect(second).toHaveBeenCalledTimes(1);
    });
});
