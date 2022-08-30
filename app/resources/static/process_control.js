(function( process_control, $, undefined ) {
    //Private Property

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
                  var pctrls = $("select[class='process_control']");
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
        $.ajax
            ({
                url: '/info',
                data: {'type': 'GET_INFO'},
                type: 'post',
                success: function(result)
                {
                  var pctrls = $("select[class='process_control']");
                  $.each(pctrls , function (index, ctrl) {
                    if (result.process == "") {
                        $(ctrl).val("_null")
                    } else {
                        console.log('yo man', ctrl)
                        $(ctrl).val(result.process)
                    }
                  });
                }
            });
    };

    function select_process(val) {
        var pctrls = $("select[class='process_control']");
                  $.each(pctrls , function (index, ctrl) {
                    $(ctrl).val("_null")
                });
    }

}( window.process_control = window.process_control || {}, jQuery ));
