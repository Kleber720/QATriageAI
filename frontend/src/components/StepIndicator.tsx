import { Check } from "lucide-react";

export type WizardStep = 1 | 2 | 3;

interface StepIndicatorProps {
  currentStep: WizardStep;
}

const STEPS: { step: WizardStep; label: string; subtitle: string }[] = [
  { step: 1, label: "Relato ou Rascunho", subtitle: "Entrada do bug" },
  { step: 2, label: "Perguntas Rápidas", subtitle: "Só o que falta" },
  { step: 3, label: "Ticket Estruturado", subtitle: "Pronto para QA" },
];

export function StepIndicator({ currentStep }: StepIndicatorProps) {
  return (
    <nav aria-label="Etapas da triagem" className="mb-8">
      <ol className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {STEPS.map((item) => {
          const isCompleted = currentStep > item.step;
          const isActive = currentStep === item.step;

          return (
            <li
              key={item.step}
              className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition ${
                isActive
                  ? "border-indigo-500/60 bg-indigo-500/10 shadow-sm shadow-indigo-500/10"
                  : isCompleted
                    ? "border-emerald-500/30 bg-emerald-500/5"
                    : "border-slate-800 bg-slate-900/50 opacity-60"
              }`}
            >
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  isCompleted
                    ? "bg-emerald-500 text-slate-950"
                    : isActive
                      ? "bg-indigo-500 text-white"
                      : "bg-slate-800 text-slate-400"
                }`}
              >
                {isCompleted ? <Check className="h-4 w-4" /> : item.step}
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-100">
                  {item.label}
                </p>
                <p className="truncate text-xs text-slate-400">{item.subtitle}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
