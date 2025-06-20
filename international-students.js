// Function to determine if a student is international based on nationality
function isInternationalStudent(nationality) {
    // Define local nationalities (assuming we're in a country that's not Afghanistan)
    const localNationalities = ['Saudi', 'Saudi Arabian']; // Add all local nationalities here
    
    // If the nationality is not in the local list, they're international
    return !localNationalities.includes(nationality);
}

// Function to count international students
function countInternationalStudents() {
    const students = document.querySelectorAll('table tbody tr');
    let internationalCount = 0;
    
    students.forEach(student => {
        const nationalityCell = student.querySelector('td:nth-child(4)'); // Assuming nationality is in the 4th column
        if (nationalityCell) {
            const nationality = nationalityCell.textContent.trim();
            if (isInternationalStudent(nationality)) {
                internationalCount++;
            }
        }
    });
    
    return internationalCount;
}

// Update the international student count in the UI
function updateInternationalStudentCount() {
    const count = countInternationalStudents();
    const internationalCountElement = document.getElementById('international-student-count');
    if (internationalCountElement) {
        internationalCountElement.textContent = count;
    }
}

// Run when the page loads
document.addEventListener('DOMContentLoaded', updateInternationalStudentCount);
