import { FEATURE_KEYS, type FeatureKey, type FormValues, type Observation } from "./types";
import { FIELDS } from "./constants";

export function emptyForm(): FormValues {
  return Object.fromEntries(FEATURE_KEYS.map((k) => [k, ""])) as FormValues;
}

export function formFromObservation(obs: Observation): FormValues {
  return Object.fromEntries(FEATURE_KEYS.map((k) => [k, obs[k] === null ? "" : String(obs[k])])) as FormValues;
}

/** Empty box = missing (null). Anything that is not a number, or is out of range, is reported. */
export function parseForm(form: FormValues): { observation: Observation | null; problems: string[] } {
  const problems: string[] = [];
  const observation = {} as Observation;
  for (const field of FIELDS) {
    const raw = form[field.key].trim();
    if (raw === "") {
      observation[field.key] = null;
      continue;
    }
    const n = Number(raw);
    if (!Number.isFinite(n)) {
      problems.push(`${field.label} is not a number`);
    } else if (field.min !== undefined && n < field.min) {
      problems.push(`${field.label} must be at least ${field.min}`);
    } else if (field.max !== undefined && n > field.max) {
      problems.push(`${field.label} must be at most ${field.max}`);
    } else {
      observation[field.key] = n;
    }
  }
  return { observation: problems.length ? null : observation, problems };
}

/** value_minus_baseline is value - baseline_mean in the training data, so it can be filled for the user. */
export function withDerived(form: FormValues): FormValues {
  const value = Number(form.value);
  const base = Number(form.baseline_mean);
  if (form.value.trim() === "" || form.baseline_mean.trim() === "" || !Number.isFinite(value) || !Number.isFinite(base)) {
    return form;
  }
  return { ...form, value_minus_baseline: String(Math.round((value - base) * 10_000) / 10_000) };
}

export function setField(form: FormValues, key: FeatureKey, raw: string, autoDerive: boolean): FormValues {
  const next = { ...form, [key]: raw };
  return autoDerive && (key === "value" || key === "baseline_mean") ? withDerived(next) : next;
}