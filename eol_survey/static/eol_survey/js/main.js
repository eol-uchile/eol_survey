function cleanerSurvey() {
    //Clean the form
    var SurveyForm = document.querySelector('#contact-form-input form');
    SurveyForm.reset();
}

var createSurvey = document.getElementById("create_survey");
var contactForm = document.querySelector(".contact-form-input");
saveSurvey = document.getElementById('view_survey');
createSurvey.addEventListener("click", function () {
    // adds a click event on create survey, calls cleanerSurvey() and resets the inputId field
    contactForm.style.display = "block";
    cleanerSurvey();
    var inputId = document.getElementById('inputId');
    inputId.value = "";
    saveSurvey.value = "Guardar Encuesta";
})

var cboSurvey = document.getElementById('select_survey_id');
var inputSurvey = document.getElementById('inputId');
var editButton = document.getElementById("edit_survey");

    cboSurvey.addEventListener('change', function(){
        if(cboSurvey.value !== '') {
            editButton.removeAttribute('disabled');
        } else {
            editButton.setAttribute('disabled', 'true');
            
        }
    })

var contactForm = document.querySelector(".contact-form-input");
editButton.addEventListener("click", function () {
    //adds a click event, if the edit form is visible, it hides it, otherwise it shows it. And change the name of the button to Edit Survey.
    const button = this; 
    const form = document.getElementById("contact-form-input");

        inputSurvey.value =cboSurvey.value;
        saveSurvey.value = "Editar Encuesta";
        contactForm.style.display = "block";    
        loadMessage();
    });

function loadcombo(){
    // load the combobox according to an api request and it is filled automatically. 
    $.ajax({
        type:'GET',
        url:'/api/get_survey_json/',
        dataType: 'json',
        success: function(data){
            var dropdown = $('#select_survey_id');
            dropdown.empty();
            dropdown.append($('<option>').text('Selecciona una encuesta').val(''));
            $.each(data.surveys, function(index, item){
                dropdown.append($('<option>').text(item.header).val(item.id));
            });
            }
        })
}

function loadMessage() {
    // query the api and if the id exists, fill in the fields so that it can be edited.
    var surveySelect = document.getElementById('inputId');
    var surveyId = surveySelect.value;
    var headerFill = document.getElementById('form-header');
    var descripFill = document.getElementById('form-description');
    var contentFill = document.getElementById('form-content');

    if (surveyId !== undefined){
        fetch('/api/message_detail?survey_id='+surveyId)
            .then(response => {
                if(!response.ok){
                    throw new Error('La solicitud a la API falló');
                }
                return response.json();
            })
            .then(data =>{
                headerFill.value = data.content.header;
                descripFill.value = data.content.description;
                contentFill.value = data.content.content;
                
                var inputDelete = document.getElementById('delete_survey');
                inputDelete.disabled = false;
                editButton.disable = true;
            })
            .catch(error => {
                console.error('Error al carga los datos de la API:', error)
            });
    } else {
        headerFill.value = '';
        campoFill.value = '';
        contentFill.value = '';
    }
}

function deleteSurvey() {
    // checks if you want to delete the survey, if yes, it sends a query to the database to delete the survey.
    var surveySelect = document.getElementById('inputId');
    var surveyId = surveySelect.value;
    var confirmDelete = confirm("¿Estás seguro de que desea eliminar esta encuesta?");
    
    if(confirmDelete){
        if (surveyId !== undefined) {
            $.ajax({
            dataType: 'json',
            type: 'POST',
            url: '/api/delete_survey/',
            data: JSON.stringify({survey_id: surveyId}),
            contentType: 'application/json',
            success: function(data) {
                var messageContainer = document.querySelector('.message-container');

                if (data.success) {
                    document.getElementById('status_survey').innerText= 'Encuesta Eliminada correctamente.';
                    messageContainer.classList.remove('no-message');
                    loadcombo();
                    cleanerSurvey();
                    contactForm.style.display = "none";
                    var inputDelete = document.getElementById('delete_survey');
                    inputDelete.disabled = true;                    
                    editButton.disabled = true;

                }
                else{
                    document.getElementById("status_survey").innerText = "Error al ingresar los datos, actualice la página e intente nuevamente. Si persiste comuníquese con mesa de ayuda.";
                    messageContainer.style.backgroundColor = "orangered";
                    messageContainer.style.lineHeight = "normal";
                }
            },
            error: function() {
                alert("Fallo :c")
            }
            })
            } else {
                alert('Por favor, selecciona una encuesta antes de eliminar.');
            }
        }

 }

$(document).ready(function () {
    loadcombo();
 })
