import React, { FC, FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { searchOutline } from "ionicons/icons";

import { useAPI } from "../../hooks";
import { Icon } from "../atoms";
import { findSearchTarget } from "../../utils";

import "./quick-search.css";

export const QuickSearch: FC = () => {
    const api = useAPI();
    const navigate = useNavigate();
    const [query, setQuery] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [searching, setSearching] = useState(false);
    const input = useRef<HTMLInputElement>(null);

    // focuses the search with the "/" key (as in other admin and
    // developer tools), unless it's typed into another field
    useEffect(() => {
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key !== "/" || event.ctrlKey || event.metaKey) return;
            const target = event.target as HTMLElement;
            if (
                target.isContentEditable ||
                ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
            )
                return;
            event.preventDefault();
            input.current?.focus();
        };
        document.addEventListener("keydown", onKeyDown);
        return () => document.removeEventListener("keydown", onKeyDown);
    }, []);

    const onSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;
        setError(null);
        setSearching(true);
        try {
            // a list that can't be retrieved doesn't fail the search, as
            // the other one is still searched, but then a missing node or
            // job is not reported as so, as it may be in that list
            let failed = false;
            const onError = () => {
                failed = true;
                return {};
            };
            const [nodes, jobs] = await Promise.all([
                api.listNodes().catch(onError),
                api.listJobs().catch(onError)
            ]);
            const path = findSearchTarget(
                query,
                Object.keys(nodes),
                Object.keys(jobs)
            );
            if (!path) {
                setError(
                    failed
                        ? `Couldn't search for "${query.trim()}", try again`
                        : `No node or job "${query.trim()}"`
                );
                return;
            }
            setQuery("");
            navigate(path);
        } finally {
            setSearching(false);
        }
    };

    return (
        <form className="quick-search" role="search" onSubmit={onSubmit}>
            <Icon
                icon={searchOutline}
                size="sm"
                style={["quick-search-icon"]}
            />
            <input
                ref={input}
                className="quick-search-input"
                type="search"
                aria-label="Go to node or job"
                placeholder="Go to node or job"
                value={query}
                readOnly={searching}
                onChange={(e) => {
                    setQuery(e.target.value);
                    setError(null);
                }}
            />
            <kbd className="quick-search-key" aria-hidden="true">
                /
            </kbd>
            {error && (
                <span className="quick-search-error" role="alert">
                    {error}
                </span>
            )}
        </form>
    );
};
