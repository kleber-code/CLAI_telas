function formatCPF(cpf) {
    cpf = cpf.replace(/\D/g, ''); // Remove non-digit characters
    if (cpf.length <= 11) {
        // CPF
        cpf = cpf.replace(/(\d{3})(\d)/, '$1.$2');
        cpf = cpf.replace(/(\d{3})(\d)/, '$1.$2');
        cpf = cpf.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
    }
    return cpf;
}

function setupCPFInput(inputId) {
    const inputElement = document.getElementById(inputId);
    if (inputElement) {
        inputElement.addEventListener('input', (event) => {
            let value = event.target.value;
            event.target.value = formatCPF(value);
        });
    }
}
