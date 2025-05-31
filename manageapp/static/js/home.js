function showSection(section) {

    const boxes = document.querySelectorAll('.box');
    boxes.forEach(box => {
        box.classList.add('hidden');
    });
    const selectedBox = document.getElementById(section);
    selectedBox.classList.remove('hidden');
}

function previewImage(event) {
    const image = document.getElementById('profileImage');
    image.src = URL.createObjectURL(event.target.files[0]);
}

function saveChanges(section) {
    alert(`Changes saved for ${section}!`);
}