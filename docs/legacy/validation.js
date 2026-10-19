const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const PHONE_REGEX = /^\+?[0-9\s().-]{7,20}$/;

function getSpecificEmailError(emailText) {
  if (!emailText.includes("@")) return "El correo debe incluir el simbolo @.";
  const [localPart, domainPart] = emailText.split("@");
  if (!localPart) return "Falta la parte local antes de @ en el correo.";
  if (!domainPart) return "Falta el dominio despues de @ en el correo.";
  if (!domainPart.includes(".")) return "El dominio del correo debe incluir un punto (por ejemplo, empresa.com).";
  return "Ingresa un correo corporativo valido.";
}

function createValidatorController(formId, validators, successText) {
  const form = document.getElementById(formId);
  if (!form) return;

  const successMessage = document.getElementById("successMessage");
  const fieldNames = Object.keys(validators);

  function getFieldElement(fieldName) {
    return document.getElementById(fieldName);
  }

  function getErrorElement(fieldName) {
    return document.getElementById(fieldName + "Error");
  }

  function setFieldState(fieldName, message) {
    const input = getFieldElement(fieldName);
    const error = getErrorElement(fieldName);
    if (!input || !error) return;

    error.setAttribute("aria-live", "assertive");
    error.setAttribute("aria-atomic", "true");
    error.textContent = message;
    const hasError = Boolean(message);
    const hasValue = input.type === "checkbox" ? input.checked : Boolean(String(input.value || "").trim());

    if (hasError) {
      input.classList.remove("border-emerald-500", "focus:ring-emerald-200");
      input.classList.add("border-red-500", "focus:ring-red-200");
      input.setAttribute("aria-invalid", "true");
    } else {
      input.classList.remove("border-red-500", "focus:ring-red-200");
      if (hasValue) {
        input.classList.add("border-emerald-500", "focus:ring-emerald-200");
      } else {
        input.classList.remove("border-emerald-500", "focus:ring-emerald-200");
      }
      input.removeAttribute("aria-invalid");
    }
  }

  function validateField(fieldName) {
    const input = getFieldElement(fieldName);
    if (!input) return true;

    const validator = validators[fieldName];
    const message = validator(input.value, input);
    setFieldState(fieldName, message);
    return !message;
  }

  function clearSuccess() {
    if (!successMessage) return;
    successMessage.classList.add("hidden");
    successMessage.textContent = "";
  }

  fieldNames.forEach((fieldName) => {
    const input = getFieldElement(fieldName);
    if (!input) return;

    input.setAttribute("aria-describedby", fieldName + "Error");

    const eventName = input.type === "checkbox" || input.tagName === "SELECT" ? "change" : "input";
    input.addEventListener(eventName, () => {
      validateField(fieldName);
      clearSuccess();
    });

    input.addEventListener("blur", () => {
      validateField(fieldName);
    });
  });

  form.addEventListener("reset", () => {
    fieldNames.forEach((fieldName) => setFieldState(fieldName, ""));
    clearSuccess();
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    const isValid = fieldNames.every((fieldName) => validateField(fieldName));
    if (!isValid) {
      clearSuccess();
      return;
    }

    if (successMessage) {
      successMessage.setAttribute("aria-live", "polite");
      successMessage.setAttribute("aria-atomic", "true");
      successMessage.textContent = successText;
      successMessage.classList.remove("hidden");
    }
    form.reset();
    fieldNames.forEach((fieldName) => setFieldState(fieldName, ""));
  });
}

createValidatorController(
  "applicationForm",
  {
    fullName: (value) => {
      const text = value.trim();
      if (!text) return "El nombre completo es obligatorio.";
      if (text.length < 3) return "El nombre debe tener al menos 3 caracteres.";
      return "";
    },
    jobTitle: (value) => {
      if (!value.trim()) return "El cargo es obligatorio.";
      return "";
    },
    email: (value) => {
      const text = value.trim();
      if (!text) return "El correo corporativo es obligatorio.";
      if (!EMAIL_REGEX.test(text)) return getSpecificEmailError(text);
      return "";
    },
    phone: (value) => {
      const text = value.trim();
      if (!text) return "El telefono es obligatorio.";
      if (!PHONE_REGEX.test(text)) return "Ingresa un telefono valido con prefijo internacional.";
      return "";
    },
    department: (value) => {
      if (!value) return "Selecciona el area principal.";
      return "";
    },
    country: (value) => {
      if (!value) return "Selecciona el pais de operacion.";
      return "";
    },
    city: (value) => {
      if (!value.trim()) return "La ciudad base es obligatoria.";
      return "";
    },
    restaurantsCount: (value) => {
      if (!value) return "El numero de locales es obligatorio.";
      const n = Number(value);
      if (!Number.isFinite(n) || n < 1) return "El numero de locales debe ser mayor a 0.";
      return "";
    },
    employeesCount: (value) => {
      if (!value) return "El numero de empleados es obligatorio.";
      const n = Number(value);
      if (!Number.isFinite(n) || n < 1) return "El numero de empleados debe ser mayor a 0.";
      return "";
    },
    annualRevenueUsd: (value) => {
      if (!value) return "La facturacion anual es obligatoria.";
      const n = Number(value);
      if (!Number.isFinite(n) || n <= 0) return "Ingresa una facturacion anual valida en USD.";
      return "";
    },
    priorityNeed: (value) => {
      if (!value) return "Selecciona una prioridad digital.";
      return "";
    },
    timeline: (value) => {
      if (!value) return "Selecciona un horizonte de implementacion.";
      return "";
    },
    preferredDate: (value) => {
      if (!value) return "La fecha de kickoff es obligatoria.";
      const selected = new Date(value + "T00:00:00");
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (selected < today) return "La fecha no puede estar en el pasado.";
      return "";
    },
    monthlyBudgetUsd: (value) => {
      if (value === "") return "El presupuesto mensual estimado es obligatorio.";
      const n = Number(value);
      if (!Number.isFinite(n) || n < 0) return "Ingresa un presupuesto mensual valido.";
      return "";
    },
    currentStack: (value) => {
      const text = value.trim();
      if (!text) return "Describe sistemas actuales y limitaciones.";
      if (text.length < 20) return "Incluye mayor detalle tecnico (minimo 20 caracteres).";
      return "";
    },
    message: () => "",
    terms: (_, input) => {
      if (!input.checked) return "Debes aceptar la politica de privacidad.";
      return "";
    },
  },
  "Application enviada con exito. El equipo Brasaland Digital revisara tu informacion y te contactara en menos de 48 horas."
);