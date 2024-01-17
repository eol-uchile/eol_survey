function loadCbAnalytics(){
    var course_id = document.getElementById('courseId').value; 
    
    $.ajax({
        url: "/survey_responses/"+course_id,
        dataType: 'json',
        cache: false,
        contentType: "application/json",
        processData: false,
        type: "GET",
        success: function(data){
            var dropdown = $('#cb_eol_survey');
            dropdown.empty();
            dropdown.append($('<option>').text('Seleccione una encuesta del curso').val(''));

            $.each(data.response, function(index, item){

                dropdown.append($('<option>').text(item.parent_display_name+' - '+ item.name_survey).val(item.location));
              
                var maxLength = 90;
                $('#cb_eol_survey > option').text(function(i, text) {
                    if (text.length > maxLength) {
                        return text.substr(0, maxLength) + '...';  
                    }
                });
            });
        },
        
        error: function(){
            console.log("Hubo un error al momento de cargar las encuestas");
        }
    })    
}
$(document).ready(function () {
    loadCbAnalytics();
 })