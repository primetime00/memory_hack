(function( process_control, $, undefined ) {
    //Private Property
    var iteration = 0
    var process_crc = 0
    var process_list = []


    //Public Property

    //Public Method
    process_control.process_changed = function(_proc) {
        var value = _proc[_proc.selectedIndex].text
        $.ajax
            ({
                url: '/info',
                data: {'type': 'SET_PROCESS', 'process': value},
                type: 'post',
                success: function(result)
                {
                  if (result.status == 'INFO_ERROR') {
                    ons.notification.toast(result.error, { timeout: 2000, animation: 'fall' })
                    select_process('_null');
                    return;
                  }
                  var pctrls = $("select.process_control");
                  $.each(pctrls , function (index, ctrl) {
                    $(ctrl).val($(_proc).val())
                  });
                  search.on_process_changed(value);
                  aob.on_process_changed(value);
                }
            });
    };

    process_control.ready = function() {
        on_ready();
    }

    //Private Methods
    function on_ready() {
        get_info()
    };

    function get_info() {
        $.post('/info', { "type": "GET_INFO", 'iteration': iteration }, populate_control);
        iteration += 1
        setTimeout(get_info, 3000)
    }

    function populate_control(result) {
        var process = result.process
        search.on_process_changed(process);
        aob.on_info_process(process);

        if (result.crc != 0 && result.crc != process_crc) {
            process_crc = result.crc
            process_list = result.processes
            populate_processes(result.processes)
        }
        var pctrls = $("select.process_control");
        $.each(pctrls , function (index, ctrl) {
          var text = $(ctrl).children(':selected').text()
          if (result.process != text) {
            $(ctrl).val(result.process == "" ? "_null"  : result.process )
          }
        });
    };

    function populate_processes(procs) {
      var pctrls = $("select.process_control");
      $.each(pctrls , function (index, ctrl) {
        $(ctrl).empty()
        $(ctrl).append($('<option>', { value: "_null", text: "" }));
        $.each(procs , function (index, value) {
            $(ctrl).append($('<option>', { value: value, text: value }));
        });
      });
    }

    function select_process(val) {
        var pctrls = $("select.process_control");
                  $.each(pctrls , function (index, ctrl) {
                    $(ctrl).val("_null")
                });
    }

}( window.process_control = window.process_control || {}, jQuery ));
