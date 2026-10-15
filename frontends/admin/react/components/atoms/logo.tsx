import React, { FC, Fragment, useId, useMemo } from "react";

import "./logo.css";

/**
 * The slices of the sliced C mark, in its 64 unit box, the middle
 * one (in the brand mint) being shifted to the right, as a line
 * that is being printed.
 */
const MARK = {
    top: "M11.51 19.5A24 24 0 0 1 52.49 19.5Z",
    middle: "M29.67 22.5H14.96A24 24 0 0 0 14.96 41.5H29.67A12 12 0 0 1 29.67 22.5Z",
    bottom: "M11.51 44.5A24 24 0 0 0 52.49 44.5Z"
};

/**
 * The centerlines of the "colony print" logotype, stroked 7 units
 * wide over an x-height from 8 to 40 units. The middle slice drops
 * the right side of the "c" (as the mark does) and the solid version,
 * used at small sizes, replaces the cuts with an open "c".
 */
const WORD = {
    full: "M3.5 24A12.5 12.5 0 1 1 28.5 24A12.5 12.5 0 1 1 3.5 24M40.5 24A12.5 12.5 0 1 1 65.5 24A12.5 12.5 0 1 1 40.5 24M77.5 -6V40M89.5 24A12.5 12.5 0 1 1 114.5 24A12.5 12.5 0 1 1 89.5 24M126.5 8V40M126.5 24A12.5 12.5 0 0 1 151.5 24V40M163.5 8V24A12.5 12.5 0 0 0 188.5 24M188.5 8V46A10 10 0 0 1 178.5 56H168M221.5 8V59.5M221.5 24A12.5 12.5 0 1 1 246.5 24A12.5 12.5 0 1 1 221.5 24M258.5 8V40M258.5 24A12.5 12.5 0 0 1 271 11.5H275M282.5 -6V1M282.5 8V40M294.5 8V40M294.5 24A12.5 12.5 0 0 1 319.5 24V40M334.5 0V40M328 11.5H344",
    middle: "M16 36.5A12.5 12.5 0 0 1 16 11.5M40.5 24A12.5 12.5 0 1 1 65.5 24A12.5 12.5 0 1 1 40.5 24M77.5 -6V40M89.5 24A12.5 12.5 0 1 1 114.5 24A12.5 12.5 0 1 1 89.5 24M126.5 8V40M126.5 24A12.5 12.5 0 0 1 151.5 24V40M163.5 8V24A12.5 12.5 0 0 0 188.5 24M188.5 8V46A10 10 0 0 1 178.5 56H168M221.5 8V59.5M221.5 24A12.5 12.5 0 1 1 246.5 24A12.5 12.5 0 1 1 221.5 24M258.5 8V40M258.5 24A12.5 12.5 0 0 1 271 11.5H275M282.5 -6V1M282.5 8V40M294.5 8V40M294.5 24A12.5 12.5 0 0 1 319.5 24V40M334.5 0V40M328 11.5H344",
    solid: "M26.24 16.83A12.5 12.5 0 1 0 26.24 31.17M40.5 24A12.5 12.5 0 1 1 65.5 24A12.5 12.5 0 1 1 40.5 24M77.5 -6V40M89.5 24A12.5 12.5 0 1 1 114.5 24A12.5 12.5 0 1 1 89.5 24M126.5 8V40M126.5 24A12.5 12.5 0 0 1 151.5 24V40M163.5 8V24A12.5 12.5 0 0 0 188.5 24M188.5 8V46A10 10 0 0 1 178.5 56H168M221.5 8V59.5M221.5 24A12.5 12.5 0 1 1 246.5 24A12.5 12.5 0 1 1 221.5 24M258.5 8V40M258.5 24A12.5 12.5 0 0 1 271 11.5H275M282.5 -6V1M282.5 8V40M294.5 8V40M294.5 24A12.5 12.5 0 0 1 319.5 24V40M334.5 0V40M328 11.5H344"
};

/**
 * The horizontal bands (in logotype units) of the slices of the
 * logotype, the ones of the mark scaled to the x-height (by 2/3),
 * so that the cuts of both line up.
 */
const SLICES = [
    { y: -20, height: 35.667 },
    { y: 17.667, height: 12.667 },
    { y: 32.333, height: 47.667 }
];

/**
 * The width and height of the logotype (in its units), and the
 * offset of the logotype after the mark in the lockup.
 */
const WORD_WIDTH = 344;
const WORD_HEIGHT = 71.5;
const LOCKUP_OFFSET = 66;

interface LogoProps {
    variant?: "lockup" | "mark" | "logotype";
    sliced?: boolean;
    height?: number;
    label?: string;
    style?: string[];
}

export const Logo: FC<LogoProps> = ({
    variant = "lockup",
    height = 32,
    sliced = height >= 48,
    label = "Colony Print",
    style = []
}) => {
    const id = useId().replace(/:/g, "");
    const classes = useMemo(
        () => ["logo", ...style].filter(Boolean).join(" "),
        [style]
    );

    // the logotype (alone or in the lockup) shares the vertical
    // extent of the logotype, with room for its ascenders and
    // descenders, the mark alone being drawn in its own box
    const width =
        variant === "mark"
            ? 64
            : variant === "logotype"
              ? WORD_WIDTH + 6
              : LOCKUP_OFFSET + WORD_WIDTH + 6;
    const viewBox =
        variant === "mark" ? "0 0 64 64" : `-3 -9 ${width} ${WORD_HEIGHT}`;
    const ratio = variant === "mark" ? 1 : width / WORD_HEIGHT;

    const mark = (
        <Fragment>
            <path className="logo-ink" d={MARK.top} />
            <path className="logo-mint" d={MARK.middle} />
            <path className="logo-ink" d={MARK.bottom} />
        </Fragment>
    );

    // the sliced logotype is drawn three times, each one clipped to
    // one of the slices, the middle one in the brand mint and kept
    // aligned (unlike the mark, so that the letters stay readable),
    // the solid one (the default below 48px of height, where the
    // cuts blur) once
    const word = sliced ? (
        <g fill="none" strokeWidth={7}>
            <defs>
                {SLICES.map((slice, index) => (
                    <clipPath key={index} id={`${id}-slice-${index}`}>
                        <rect
                            x={-20}
                            y={slice.y}
                            width={420}
                            height={slice.height}
                        />
                    </clipPath>
                ))}
            </defs>
            <path
                className="logo-ink-stroke"
                clipPath={`url(#${id}-slice-0)`}
                d={WORD.full}
            />
            <path
                className="logo-mint-stroke"
                clipPath={`url(#${id}-slice-1)`}
                d={WORD.middle}
            />
            <path
                className="logo-ink-stroke"
                clipPath={`url(#${id}-slice-2)`}
                d={WORD.full}
            />
        </g>
    ) : (
        <path
            className="logo-ink-stroke"
            fill="none"
            strokeWidth={7}
            d={WORD.solid}
        />
    );

    return (
        <svg
            className={classes}
            viewBox={viewBox}
            width={height * ratio}
            height={height}
            role={label ? "img" : undefined}
            aria-label={label || undefined}
            aria-hidden={label ? undefined : true}
        >
            {variant === "mark" && mark}
            {variant === "logotype" && word}
            {variant === "lockup" && (
                <Fragment>
                    <g transform="translate(-13.43 -13.33) scale(1.1667)">
                        {mark}
                    </g>
                    <g transform={`translate(${LOCKUP_OFFSET} 0)`}>{word}</g>
                </Fragment>
            )}
        </svg>
    );
};
