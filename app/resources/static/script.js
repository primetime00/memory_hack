(function( script, $, undefined ) {

    //Private Property
    var script_list = [];

    var requested_ui = false;
    var script_select;
    var current_script;


    //Public Property
    script.test = "Bacon Strips";

    //Public Method
    script.ready = function() {
        script_select = $("#script_names");
        current_script = $("#current_script");

        check_script_status()
    }

    script.script_name_selected = function(script) {
        var unload = script === '_null';
        var name = unload ? "" : script;
        $.post('/script', { "type": "SCRIPT_LOAD", "name": name, "unload": unload}, on_script_status);
    }

    script.script_interact_value = function(event) {
        var val = event.currentTarget.value
        var id = event.currentTarget.id.replace('input_', '')
        var el = $("#"+id)[0]
        if (el.checked !== undefined) {
            el.checked = false
        }
        $("#"+id).attr('disabled', 'disabled')
        post_interact(id, {'value': val})
    }

    script.script_interact_button = function(event) {
        var id = event.currentTarget.id
        post_interact(id, {})
    }

    script.script_interact_select = function(event) {
        var id = event.currentTarget.id
        post_interact(id, {"value": event.currentTarget.value})
    }

    script.script_interact_multi_select = function(event) {
        var id = event.currentTarget.id
        var root = $(event.currentTarget)
        post_interact(id, {"value": root.val()})
    }


    script.script_interact_toggle = function(event) {
        var target = event.target
        post_interact(event.target.id, {"checked": target.checked})
    }

    script.script_upload_file_changed = function(file) {
        var fname = file.name
        var ext = fname.slice((fname.lastIndexOf(".") - 1 >>> 0) + 2)
        if (ext.toLowerCase() != 'py') {
            ons.notification.toast('Script must have a Python extension (.py)', { timeout: 2000, animation: 'fall' })
            return
        }
        if (file.size > 400000) {
            ons.notification.toast('File must be under 400KB', { timeout: 2000, animation: 'fall' })
            return
        } else if (file.size <= 200) {
            ons.notification.toast('Script file is too small.', { timeout: 2000, animation: 'fall' })
            return
        }
        var reader = new FileReader();
        reader.readAsText(file, 'UTF-8');
        reader.onload = function(event) {
            var result = event.target.result;
            var fileName = file.name;
            $.post('/script', { "type": "SCRIPT_UPLOAD_FILE", data: result, name: fileName }, on_script_upload_complete);
        }
    }


    //Private Method
    function on_script_status(result) {
        var status = result.status;
        if (result.hasOwnProperty('scripts')) {
            populate_scripts(result.scripts)
        }
        switch (status) {
            case 'SCRIPT_STATUS': break;
            case 'SCRIPT_LOADED': on_script_loaded(result.current); break;
            case 'SCRIPT_NOT_READY': on_script_not_ready(result.current); break;
            case 'SCRIPT_IS_READY': on_script_ready(result.current); break;
            case 'SCRIPT_UNLOADED': on_script_ui_get(""); break;
            case 'SCRIPT_UI_GET':  on_script_ui_get(result.ui); break;
            case 'SCRIPT_ERROR': on_script_error(result.error); break;
            default: break;
        }
        if (has(result, 'controls')) {
            update_controls(result.controls)
        }
        if (result.hasOwnProperty('repeat')) {
            if (!requested_ui) { //our script is running, but no UI is showing
                script_select.val(result.current);
                on_script_ready(result.current);
            } else {
                setTimeout(check_script_status, result.repeat);
            }
        }
    }

    function on_script_ui_get(ui) {
        requested_ui = true;
        current_script.html(ui);
        //at this point the script is running, we just need to check in
        setTimeout(check_script_status, 1000)
    }

    function on_script_loaded(name) {
        $.post('/script', { "type": "SCRIPT_IS_READY"}, on_script_status);
    }

    function on_script_not_ready(name) {
        setTimeout(function() {on_script_loaded(name)}, 300);
    }

    function on_script_ready(name) {
        $.post('/script', { "type": "SCRIPT_UI_GET", "name": name}, on_script_status);
    }

    function on_script_interacted(result) {
    }

    function on_script_error(msg) {
        ons.notification.toast(msg, { timeout: 5000, animation: 'fall' })
        script_select.val('_null')
        script.script_name_selected('_null')
    }

    function update_controls(controls) {
        $.each(controls , function (id, instructions) {
            $.each(instructions , function (index, instruction) {
                switch (instruction.op) {
                    case "add_attribute":
                        $("#"+id).attr(instruction.data.attr, instruction.data.value)
                        break;
                    case "remove_attribute":
                        $("#"+id).removeAttr(instruction.data.attr)
                        break;
                    case "prop":
                        $("#"+id).prop(instruction.data.name, instruction.data.value)
                        break;
                    case "value":
                        $("#"+id).val(instruction.data.value)
                        break;
                    case "script":
                        Function('"use strict"; '+ instruction.data.script)()
                        break;
                    case "inner-html":
                        $("#"+id).empty()
                        $("#"+id).append(instruction.data.html)
                        break;
                    default:
                        break;
                }
            });
        });
    }

    function check_script_status() {
        $.post('/script', { "type": "SCRIPT_STATUS"}, on_script_status);
    }

    function post_interact(id, data) {
        $.ajax ({
            url: "/script",
            type: "POST",
            data: JSON.stringify({ "type": "SCRIPT_INTERACT", "id": id, "data": data }),
            dataType: "json",
            contentType: "application/json; charset=utf-8",
            success: (res) => {$("#"+id).removeAttr('disabled');  on_script_interacted(res);}
            });
    }

    function populate_scripts(scripts) {
        if (script_list.length != scripts.length) {
            var current = script_list.length > 0 ? script_select.val() : undefined;
            script_list = scripts;
            script_select.empty();
            if (scripts.length > 0) {
                script_select.append($('<option>', { value: "_null", text: "" }));
                $.each(scripts , function (index, value) {
                    script_select.append($('<option>', { value: value, text: value }));
                });
            }
            if (current !== undefined) {
                script_select.val(current)
            }
        }
    }

    function on_script_upload_complete(result) {
        if (result.status == "SCRIPT_ERROR") {
            ons.notification.toast(result.error, { timeout: 2000, animation: 'fall' })
            return
        }
        if (result.hasOwnProperty('scripts')) {
            ons.notification.toast(`Script ${result.name} uploaded.`, { timeout: 2000, animation: 'fall' })
            populate_scripts(result.scripts)
        }
    };

    function has(target, path) {
        if (typeof target != 'object' || target == null) {
            return false;
        }
        var parts = path.split('.');

        while(parts.length) {
            var branch = parts.shift();
            if (!(branch in target)) {
                return false;
            }

            target = target[branch];
        }
        return true;
    }




}( window.script = window.script || {}, jQuery ));
