import React, { FC, HTMLAttributes, useMemo } from "react";
import { defineCustomElement } from "ionicons/components/ion-icon.js";

import "./icon.css";

declare module "react" {
    // eslint-disable-next-line @typescript-eslint/no-namespace
    namespace JSX {
        interface IntrinsicElements {
            "ion-icon": HTMLAttributes<HTMLElement> & {
                class?: string;
                icon?: string;
            };
        }
    }
}

// registers the ion-icon web component, that draws the icons
// from their (SVG) data imported from ionicons/icons, so that
// only the icons in use are bundled and nothing is fetched
defineCustomElement();

interface IconProps {
    icon: string;
    size?: "sm" | "md" | "lg";
    label?: string;
    style?: string[];
}

export const Icon: FC<IconProps> = ({
    icon,
    size = "md",
    label,
    style = []
}) => {
    const classes = useMemo(
        () =>
            ["icon", `icon-${size}`, ...style]
                .filter(Boolean)
                .join(" "),
        [size, style]
    );
    return (
        <ion-icon
            class={classes}
            icon={icon}
            role={label ? "img" : undefined}
            aria-label={label}
            aria-hidden={label ? undefined : "true"}
        />
    );
};
