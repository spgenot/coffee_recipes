// Form validation and interactivity

document.addEventListener('DOMContentLoaded', function() {
    // Form validation
    const entryForm = document.getElementById('entry-form');
    if (entryForm) {
        entryForm.addEventListener('submit', function(e) {
            if (!validateForm()) {
                e.preventDefault();
                return false;
            }
        });

        // Real-time validation for numeric inputs
        const inputWeight = document.getElementById('input_weight');
        const outputWeight = document.getElementById('output_weight');

        if (inputWeight) {
            inputWeight.addEventListener('input', function() {
                validateNumericInput(this);
                updateExtractionRatioPreview();
            });
        }

        if (outputWeight) {
            outputWeight.addEventListener('input', function() {
                validateNumericInput(this);
                updateExtractionRatioPreview();
            });
        }
    }

    // Coffee autocomplete enhancement
    const coffeeInput = document.getElementById('coffee');
    if (coffeeInput) {
        // Enhance the datalist with better UX
        coffeeInput.addEventListener('input', function() {
            const value = this.value.toLowerCase();
            const suggestions = document.getElementById('coffee-suggestions');
            if (suggestions) {
                const options = suggestions.querySelectorAll('option');
                options.forEach(option => {
                    if (option.value.toLowerCase().includes(value) || value === '') {
                        option.style.display = '';
                    } else {
                        option.style.display = 'none';
                    }
                });
            }
        });

        // Focus enhancement
        coffeeInput.addEventListener('focus', function() {
            this.style.borderColor = '#8B4513';
        });
    }
});

function validateForm() {
    const coffee = document.getElementById('coffee');
    const grinderSetting = document.getElementById('grinder_setting');
    const inputWeight = document.getElementById('input_weight');
    const outputWeight = document.getElementById('output_weight');

    let isValid = true;

    // Validate coffee
    if (coffee && !coffee.value.trim()) {
        showFieldError(coffee, 'Coffee name is required');
        isValid = false;
    } else if (coffee) {
        clearFieldError(coffee);
    }

    // Validate grinder setting
    if (grinderSetting && !grinderSetting.value.trim()) {
        showFieldError(grinderSetting, 'Grinder setting is required');
        isValid = false;
    } else if (grinderSetting) {
        clearFieldError(grinderSetting);
    }

    // Validate input weight
    if (inputWeight) {
        if (!inputWeight.value.trim()) {
            showFieldError(inputWeight, 'Input weight is required');
            isValid = false;
        } else if (!isValidNumber(inputWeight.value)) {
            showFieldError(inputWeight, 'Input weight must be a valid number');
            isValid = false;
        } else if (parseFloat(inputWeight.value) <= 0) {
            showFieldError(inputWeight, 'Input weight must be greater than 0');
            isValid = false;
        } else {
            clearFieldError(inputWeight);
        }
    }

    // Validate output weight
    if (outputWeight) {
        if (!outputWeight.value.trim()) {
            showFieldError(outputWeight, 'Output weight is required');
            isValid = false;
        } else if (!isValidNumber(outputWeight.value)) {
            showFieldError(outputWeight, 'Output weight must be a valid number');
            isValid = false;
        } else if (parseFloat(outputWeight.value) <= 0) {
            showFieldError(outputWeight, 'Output weight must be greater than 0');
            isValid = false;
        } else {
            clearFieldError(outputWeight);
        }
    }

    return isValid;
}

function validateNumericInput(input) {
    const value = input.value.trim();
    if (value && !isValidNumber(value)) {
        input.style.borderColor = '#DC3545';
    } else if (value && parseFloat(value) <= 0) {
        input.style.borderColor = '#DC3545';
    } else {
        input.style.borderColor = '';
    }
}

function isValidNumber(value) {
    return !isNaN(value) && !isNaN(parseFloat(value)) && isFinite(value);
}

function showFieldError(field, message) {
    clearFieldError(field);
    field.style.borderColor = '#DC3545';
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'field-error';
    errorDiv.style.color = '#DC3545';
    errorDiv.style.fontSize = '0.875rem';
    errorDiv.style.marginTop = '0.25rem';
    errorDiv.textContent = message;
    
    field.parentNode.appendChild(errorDiv);
}

function clearFieldError(field) {
    field.style.borderColor = '';
    const errorDiv = field.parentNode.querySelector('.field-error');
    if (errorDiv) {
        errorDiv.remove();
    }
}

function updateExtractionRatioPreview() {
    const inputWeight = document.getElementById('input_weight');
    const outputWeight = document.getElementById('output_weight');
    
    if (inputWeight && outputWeight && inputWeight.value && outputWeight.value) {
        const input = parseFloat(inputWeight.value);
        const output = parseFloat(outputWeight.value);
        
        if (input > 0 && output > 0) {
            const ratio = (output / input).toFixed(2);
            // You could display this in a preview element if desired
            // For now, we'll just ensure the form is valid
        }
    }
}

// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(function(flash) {
        setTimeout(function() {
            flash.style.transition = 'opacity 0.5s';
            flash.style.opacity = '0';
            setTimeout(function() {
                flash.remove();
            }, 500);
        }, 5000);
    });
});
