import React, { FC, ReactNode, useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";

import { Button, Icon, Text, Title } from "../atoms";

import "./confirm-dialog.css";

interface ConfirmDialogProps {
    title: string;
    message: ReactNode;
    confirmLabel: string;
    icon?: string;
    onConfirm: () => void;
    onCancel: () => void;
}

export const ConfirmDialog: FC<ConfirmDialogProps> = ({
    title,
    message,
    confirmLabel,
    icon,
    onConfirm,
    onCancel
}) => {
    const id = useId();
    const dialog = useRef<HTMLDivElement>(null);
    const cancel = useRef(onCancel);

    // keeps the cancel handler of the last render, used by the escape
    // key, as the components that render the dialog create a new one
    // each time
    useEffect(() => {
        cancel.current = onCancel;
    }, [onCancel]);

    // focuses the cancel action (the safe one) once shown, cancels the
    // dialog with the escape key, keeps the focus in its actions (as the
    // page behind it can't be used), and gives the focus back to the
    // element that had it (e.g., the button that opened it) once gone,
    // the keys being handled before the page and kept from it, as its
    // shortcuts (e.g., the "/" of the quick search) would take the focus
    // out of the dialog
    useEffect(() => {
        const previous = document.activeElement as HTMLElement | null;
        dialog.current?.querySelector("button")?.focus();
        const onKeyDown = (event: KeyboardEvent) => {
            event.stopPropagation();
            if (event.key === "Escape") cancel.current();
            if (event.key !== "Tab" || !dialog.current) return;
            const buttons = Array.from(
                dialog.current.querySelectorAll("button")
            );
            const index = buttons.indexOf(
                document.activeElement as HTMLButtonElement
            );
            const step = event.shiftKey ? -1 : 1;
            event.preventDefault();
            buttons[(index + step + buttons.length) % buttons.length].focus();
        };
        document.addEventListener("keydown", onKeyDown, true);
        return () => {
            document.removeEventListener("keydown", onKeyDown, true);
            previous?.focus();
        };
    }, []);

    // renders the dialog in the body of the page, so that it covers the
    // page even when opened from an element that is moved (e.g., the
    // side bar that slides in on the small screens)
    return createPortal(
        <div
            className="confirm-dialog-overlay"
            onClick={(e) => {
                if (e.target === e.currentTarget) onCancel();
            }}
        >
            <div
                ref={dialog}
                className="confirm-dialog"
                role="dialog"
                aria-modal="true"
                aria-labelledby={`${id}-title`}
                aria-describedby={`${id}-message`}
            >
                <div className="confirm-dialog-body">
                    {icon && (
                        <span className="confirm-dialog-icon">
                            <Icon icon={icon} />
                        </span>
                    )}
                    <div className="confirm-dialog-text">
                        <Title
                            level={2}
                            id={`${id}-title`}
                            style={["confirm-dialog-title"]}
                        >
                            {title}
                        </Title>
                        <Text variant="secondary" id={`${id}-message`}>
                            {message}
                        </Text>
                    </div>
                </div>
                <div className="confirm-dialog-actions">
                    <Button variant="secondary" size="sm" onClick={onCancel}>
                        Cancel
                    </Button>
                    <Button variant="danger" size="sm" onClick={onConfirm}>
                        {icon && <Icon icon={icon} size="sm" />}
                        {confirmLabel}
                    </Button>
                </div>
            </div>
        </div>,
        document.body
    );
};
