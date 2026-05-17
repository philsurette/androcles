import { useEffect, useId, useRef, useState } from "react";

export type PracticeSelectOption = {
  value: string;
  label: string;
};

type PracticeSelectProps = {
  label: string;
  value: string;
  options: PracticeSelectOption[];
  onSelect: (nextValue: string) => void;
  disabled?: boolean;
};

export function PracticeSelect({
  label,
  value,
  options,
  onSelect,
  disabled = false
}: PracticeSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const selectRef = useRef<HTMLDivElement | null>(null);
  const selectId = useId();

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const onPointerDown = (event: PointerEvent) => {
      if (!selectRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [isOpen]);

  useEffect(() => {
    if (!disabled) {
      return;
    }
    setIsOpen(false);
  }, [disabled]);

  const selectedLabel = options.find((option) => option.value === value)?.label ?? value;

  return (
    <div className="practice-select-wrap" ref={selectRef}>
      <button
        type="button"
        className="practice-select-trigger"
        aria-label={label}
        title={label}
        aria-expanded={isOpen}
        aria-controls={`${selectId}-options`}
        onClick={() => setIsOpen((current) => !current)}
        disabled={disabled}
      >
        <span>{selectedLabel}</span>
        <span className="practice-select-caret" aria-hidden="true">
          ▾
        </span>
      </button>
      <div id={`${selectId}-options`} role="listbox" className={`practice-select-options ${isOpen ? "open" : ""}`} aria-label={label}>
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            role="option"
            aria-selected={option.value === value}
            className={option.value === value ? "practice-select-option active" : "practice-select-option"}
            onClick={() => {
              onSelect(option.value);
              setIsOpen(false);
            }}
            disabled={disabled}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
