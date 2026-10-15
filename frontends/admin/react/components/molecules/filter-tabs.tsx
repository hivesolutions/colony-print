import React from "react";

import "./filter-tabs.css";

interface FilterTab<T extends string> {
    value: T;
    label: string;
    count?: number;
}

interface FilterTabsProps<T extends string> {
    tabs: FilterTab<T>[];
    value: T;
    onChange: (value: T) => void;
    label?: string;
    variant?: "segmented" | "underline";
}

export function FilterTabs<T extends string>({
    tabs,
    value,
    onChange,
    label,
    variant = "segmented"
}: FilterTabsProps<T>) {
    return (
        <div
            className={`filter-tabs filter-tabs-${variant}`}
            role="group"
            aria-label={label}
        >
            {tabs.map((tab) => (
                <button
                    key={tab.value}
                    type="button"
                    className={
                        tab.value === value
                            ? "filter-tabs-tab filter-tabs-tab-active"
                            : "filter-tabs-tab"
                    }
                    aria-pressed={tab.value === value}
                    onClick={() => onChange(tab.value)}
                >
                    {tab.label}
                    {tab.count !== undefined && (
                        <span className="filter-tabs-count">{tab.count}</span>
                    )}
                </button>
            ))}
        </div>
    );
}
