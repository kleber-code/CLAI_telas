function printReport(elementSelector) {
    const printContent = document.querySelector(elementSelector).innerHTML;
    const printWindow = window.open('', '_blank');
    
    printWindow.document.write('<html><head><title>Imprimir Relatório</title>');
    
    // Copy all stylesheets from the main window to the new window
    const stylesheets = document.querySelectorAll('link[rel="stylesheet"]');
    stylesheets.forEach(sheet => {
        printWindow.document.write(sheet.outerHTML);
    });
    
    printWindow.document.write('</head><body>');
    printWindow.document.write(printContent);
    printWindow.document.write('</body></html>');
    
    printWindow.document.close(); // Necessary for some browsers
    
    printWindow.onload = function() { // Wait for the content to load
        printWindow.focus(); // Necessary for some browsers
        printWindow.print();
        printWindow.close();
    };
}
