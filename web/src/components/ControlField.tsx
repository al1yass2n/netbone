import { CircleAlert, Info, Network, SlidersHorizontal } from "lucide-react";
import type { ControlSpec, ControlValue, OptionSpec } from "../types";
import { formatValue } from "../utils";
import { Hint } from "./Hint";

interface ControlFieldProps {
  control: ControlSpec;
  value: ControlValue | undefined;
  onChange: (name: string, value: ControlValue) => void;
  compactChoices?: boolean;
}

export function ControlField({ control, value, onChange, compactChoices = false }: ControlFieldProps) {
  if (control.control === "notice") {
    const weightRequirement = control.name === "weight_requirement";
    const Icon = weightRequirement ? CircleAlert : Info;
    return (
      <div className={weightRequirement ? "inline-notice inline-notice--warning" : "inline-notice"}>
        <Icon size={16} aria-hidden="true" />
        <span>{control.label}</span>
      </div>
    );
  }

  if (control.control === "checkbox") {
    return (
      <label className={`toggle-row${control.disabled ? " is-disabled" : ""}`}>
        <span>
          <strong>{control.label}</strong>
          {control.description && <small>{control.description}</small>}
        </span>
        <input
          type="checkbox"
          checked={Boolean(value)}
          disabled={control.disabled}
          onChange={(event) => onChange(control.name, event.target.checked)}
        />
        <i aria-hidden="true" />
      </label>
    );
  }

  if (control.control === "select" && control.options?.some((option) => option.description)) {
    return (
      <fieldset className="choice-field" disabled={control.disabled}>
        <legend>{control.label}</legend>
        {control.description && <p>{control.description}</p>}
        <div className={compactChoices ? "choice-grid choice-grid--compact" : "choice-grid"}>
          {control.options.map((option) => (
            <label className="choice-option" key={option.value}>
              <input
                type="radio"
                name={control.name}
                value={option.value}
                checked={String(value) === option.value}
                disabled={option.disabled}
                onChange={() => onChange(control.name, option.value)}
              />
              <span>
                {!compactChoices && option.illustration && <OptionIllustration option={option} />}
                <strong>{option.label}</strong>
                <small>{option.description}</small>
              </span>
            </label>
          ))}
        </div>
        {control.disabled_reason && <small className="disabled-reason">{control.disabled_reason}</small>}
      </fieldset>
    );
  }

  if (control.control === "range") {
    const minimum = control.min ?? 0;
    const maximum = control.max ?? 1;
    const step = control.step ?? Math.max((maximum - minimum) / 100, 0.0001);
    const numberValue = Number(value ?? control.default ?? minimum);
    const clampedValue = Math.min(maximum, Math.max(minimum, numberValue));
    return (
      <div className="range-control">
        <div className="control-heading">
          <div className="label-with-hint">
            <label htmlFor={`control-${control.name}`}>{control.label}</label>
            {control.description && <Hint label={`About ${control.label}`}>{control.description}</Hint>}
          </div>
          <output>{control.name === "fraction" ? `${(numberValue * 100).toFixed(1)}%` : formatValue(numberValue)}</output>
        </div>
        <div className="range-inputs">
          <input
            id={`control-${control.name}`}
            type="range"
            min={minimum}
            max={maximum}
            step={step}
            value={clampedValue}
            disabled={control.disabled}
            onChange={(event) => onChange(control.name, Number(event.target.value))}
          />
          <input
            type="number"
            aria-label={`${control.label} exact value`}
            min={minimum}
            max={maximum}
            step={step}
            value={numberValue}
            disabled={control.disabled}
            onChange={(event) => onChange(control.name, event.target.value === "" ? "" : Number(event.target.value))}
          />
        </div>
        <div className="range-scale" aria-hidden="true">
          <span>{formatValue(minimum)}</span>
          <span>{formatValue(maximum)}</span>
        </div>
      </div>
    );
  }

  return (
    <label className={`field${control.disabled ? " is-disabled" : ""}`}>
      <span>{control.label}</span>
      {control.control === "select" ? (
        <select
          value={String(value ?? control.default ?? "")}
          disabled={control.disabled}
          required={control.required}
          onChange={(event) => onChange(control.name, event.target.value)}
        >
          {control.options?.map((option) => (
            <option key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>
      ) : (
        <input
          type="number"
          value={String(value ?? control.default ?? "")}
          min={control.min}
          max={control.max}
          step={control.step ?? "any"}
          disabled={control.disabled}
          required={control.required}
          inputMode={Number.isInteger(control.step) ? "numeric" : "decimal"}
          onChange={(event) => onChange(control.name, event.target.value === "" ? "" : Number(event.target.value))}
        />
      )}
      {control.description && <small>{control.description}</small>}
      {control.disabled_reason && <small className="disabled-reason">{control.disabled_reason}</small>}
    </label>
  );
}

function OptionIllustration({ option }: { option: OptionSpec }) {
  const illustration = option.illustration || {};
  if (illustration.kind === "endpoint") {
    return (
      <span className="endpoint-illustration" aria-hidden="true">
        <b>{String(illustration.left || "i")}</b>
        <i />
        <em>{String(illustration.rule || "rule")}</em>
        <i />
        <b>{String(illustration.right || "j")}</b>
        <small>{String(illustration.result || "")}</small>
      </span>
    );
  }
  return (
    <span className="generic-illustration" aria-hidden="true">
      {illustration.kind === "network" ? <Network size={24} /> : <SlidersHorizontal size={24} />}
    </span>
  );
}
