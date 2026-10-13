export function personNameRules({ required = true, label = 'Name' } = {}) {
  const rules = [];
  if (required) {
    rules.push({ required: true, message: `Please enter ${label.toLowerCase()}` });
  }
  rules.push({
    validator: (_, value) => {
      if (!value) return Promise.resolve();
      if (value !== value.trim()) {
        return Promise.reject(new Error(`${label} cannot have leading or trailing spaces`));
      }
      if (/  +/.test(value)) {
        return Promise.reject(new Error(`${label} cannot have consecutive spaces`));
      }
      if (String(value).trim().length < 2) {
        return Promise.reject(new Error(`${label} must be at least 2 characters`));
      }
      return Promise.resolve();
    },
  });
  return rules;
}

export function passwordNoSpaceRules({
  required = true,
  min = 8,
  requiredMessage = 'Please enter password',
} = {}) {
  const rules = [];
  if (required) {
    rules.push({ required: true, message: requiredMessage });
  }
  if (min) {
    rules.push({ min, message: `Min ${min} characters` });
  }
  rules.push({
    validator: (_, value) => {
      if (!value) return Promise.resolve();
      if (value.includes(' ')) {
        return Promise.reject(new Error('Password cannot contain spaces'));
      }
      return Promise.resolve();
    },
  });
  return rules;
}

export function personNameError(value, label = 'Name') {
  const text = String(value ?? '');
  if (!text.trim() || text.trim().length < 2) return `${label} is required`;
  if (text !== text.trim()) return `${label} cannot have leading or trailing spaces`;
  if (/  +/.test(text)) return `${label} cannot have consecutive spaces`;
  return null;
}
