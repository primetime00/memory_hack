(function( codelist, $, undefined ) {
    //Private Property
    var sel_codelist_process;
    var div_codelist_block;
    var row_codelist_loadsave;
    var sel_codelist_file;
    var btn_add_code;
    var btn_paste_code;

    var code_list;
    var code_data;
    var aob_resolve_map = {}
    var pointer_resolve_map = {}
    var value_map = {}

    //public vars
    codelist.updater = null

    //Public Method
    codelist.on_process_changed = function(process) {
        process_control.request_process(process, 'codelist', function(result){
            if (!result.success) {
                set_process('_null')
                ons.notification.toast(result.error, { timeout: 4000, animation: 'fall' })
            } else {
                set_process(process)
            }
        })
    };

    codelist.on_update_process_list = function(process_list_add, process_list_remove) {
        var options = sel_codelist_process.children('option') ;
        var selected = sel_codelist_process.find('option:selected')
        if (process_list_remove.includes(selected.val())) {
            div_codelist_block.hide()
        }
        for (var i=options.length-1; i>=0; i--) {
            var option=options[i]
            if (process_list_remove.includes(option.value)) {
                option.remove()
            }
        }
        var f = sel_codelist_process.find('option:first')
        for (const item of process_list_add) {
            f.after($('<option>', {value: item, text: item}))
            f = sel_codelist_process.find('option:last')
        }
    }

    codelist.on_update_selected_process = function(process_name) {
        var value = sel_codelist_process.val()
        if (value != process_name){
            set_process(process_name)
        }
    }

    codelist.on_tab_set = function(tab) {
        if (tab !== 'codelist') {
            if (codelist.updater !== null) {
                clearTimeout(codelist.updater)
                codelist.updater = null
            }
        } else {
            if (codelist.updater === null) {
                codelist.updater = setTimeout(()=>{$.send('/codelist', { "command": "CODELIST_STATUS" }, on_codelist_status);}, 100)
            }
        }
    };


    codelist.ready = function()  {
        sel_codelist_process = $("#codelist_process");
        div_codelist_block = $("#codelist_block");
        btn_add_code = $("#add_new_code_button");
        btn_add_code[0].hide()
        btn_paste_code = $("#paste_new_code_button");
        btn_paste_code[0].hide()
        row_codelist_loadsave = $("#row_codelist_loadsave");
        sel_codelist_file = $("#codelist_file_selection")
        component_list.forEach(item => {
            item['obj'] = $("#"+item.id)
            apply_events(item)
        })

    };

    apply_events = function(component) {
        if (has(component, 'changed')) {
            component.obj.bind('change', {component: component}, (event) => event.data.component.changed(event.data.component))
        }
        if (has(component, 'children')) {
            component.children.forEach((item, index) => {
                if (Array.isArray(item)) {
                    item.forEach((sub) => {apply_events(sub)})
                } else {
                    apply_events(item)
                }
            })
        }
    }

    codelist.code_value_changed = function(did_blur, ele, index) {
        event.stopPropagation()
        if (!did_blur) {
            if(event.key === 'Enter' || event.key === 'Return'  || event.keyCode == 13) {
                ele.blur()
            }
        } else {
            $.send('/codelist', {'command': 'CODELIST_WRITE', 'index': index, 'value': ele.value}, on_codelist_status)
        }
    }

    codelist.code_name_changed = function(did_blur, ele, index) {
        if (!did_blur) {
            if(event.key === 'Enter' || event.key === 'Return'  || event.keyCode === 13) {
                ele.blur()
            }
        }
        else {
            $.send('/codelist', {'command': 'CODELIST_NAME', 'index': index, 'name': ele.value}, on_codelist_status)
        }
    }

    codelist.code_size_changed = function(ele, index) {
        $.send('/codelist', { 'command': "CODELIST_SIZE", 'index': index, 'size': ele.value}, on_codelist_status);
    }

    codelist.code_freeze_changed = function(ele, index) {
        $.send('/codelist', { 'command': "CODELIST_FREEZE", 'index': index, 'freeze': ele.checked}, function(result) {
            var st = result.frozen.set
            $(ele).prop("checked", st);
            on_codelist_status(result)
        });
    }

    codelist.on_refresh = function(element, index) {
        $.send('/codelist', { 'command': "CODELIST_REFRESH", 'index': index}, on_codelist_status);
    }


    codelist.code_menu_clicked = function(ele, index) {
        ons.createElement('code_menu', { append: true }).then(function(popover) {

            items = $(popover).find('ons-list-item')
            for (i=0; i<items.length; i++) {
                var item = items[i]
                if (item.getAttribute("name") === 'address_to_aob' && document.clipboard.has_address() && !document.clipboard.has_pointer() && aob_resolve_map.hasOwnProperty(index) && aob_resolve_map[index].hasOwnProperty('Addresses') && aob_resolve_map[index]['Addresses'].length > 0) {
                    $(item).removeClass('hidden')
                }
                $(item).bind('click', {list_id: item.getAttribute("name"), code_index: index}, (event) => {codelist.option_clicked(event.data.list_id, event.data.code_index); popover.hide()})
            }
            popover.show("#"+ele.id);
        });
    }

    codelist.option_clicked = function(list_id, code_index) {
        switch (list_id) {
            case 'edit':
                var source = code_data[code_index]['Source']
                var dt = {'title': 'Edit Code', 'index': code_index}
                if (source === 'address') {
                    if (code_data[code_index]['Address'].toString().indexOf(':') >= 0) {
                        dt['address'] = code_data[code_index]['Address'].toString()
                    } else {
                        dt['address'] = code_data[code_index]['Address'].toString(16).toUpperCase()
                    }
                } else if (source === 'pointer') {
                    if (code_data[code_index]['Address'].toString().indexOf(':') >= 0) {
                        dt['pointer'] = code_data[code_index]['Address'].toString()
                    } else {
                        dt['pointer'] = code_data[code_index]['Address'].toString(16).toUpperCase()
                    }
                    dt['offsets'] = code_data[code_index]['Offsets']
                } else {
                    dt['aob'] = code_data[code_index]['AOB']
                    dt['offset'] = code_data[code_index]['Offset']
                }
                component_code_dialog.create(dt)
               break
            case 'copy':
                var source = code_data[code_index]['Source']
                var dt = {'title': 'Copy Code'}
                if (source === 'address') {
                    dt['address'] = code_data[code_index]['Address']
                } else if (source === 'pointer') {
                    dt['pointer'] = code_data[code_index]['Address']
                    dt['offsets'] = code_data[code_index]['Offsets']
                } else {
                    dt['aob'] = code_data[code_index]['AOB']
                    dt['offset'] = code_data[code_index]['Offset']
                }
                component_code_dialog.create(dt)
               break
            case 'delete':
                $.send('/codelist', { 'command': "CODELIST_DELETE_CODE", 'index': code_index}, on_codelist_status);
                break
            case 'address_to_aob':
                var new_address = document.clipboard.data.address
                var offset = parseInt(code_data[code_index].Offset, 16)
                var selected = code_data[code_index].Selected
                var resolves = aob_resolve_map[code_index]
                var resolved = selected - offset
                var new_offset = new_address - resolved
                var cmd = { 'command': "CODELIST_ADD_CODE", 'type': 'aob_from_address',
                              'address': new_address,
                              'index': code_index}

                $.send('/codelist', cmd, on_codelist_status);
                break
            case 'rebase':
                var source = code_data[code_index]['Source']
                var dt = {'index': code_index, 'source': source}
                if (source === 'address') {
                    if (code_data[code_index]['Address'].toString().indexOf(':') >= 0) {
                        dt['address'] = code_data[code_index]['Address'].toString()
                    } else {
                        dt['address'] = code_data[code_index]['Address'].toString(16).toUpperCase()
                    }
                } else if (source === 'pointer') {
                    if (code_data[code_index]['Address'].toString().indexOf(':') >= 0) {
                        dt['pointer'] = code_data[code_index]['Address'].toString()
                    } else {
                        dt['pointer'] = code_data[code_index]['Address'].toString(16).toUpperCase()
                    }
                    dt['offsets'] = code_data[code_index]['Offsets']
                } else {
                    dt['aob'] = code_data[code_index]['AOB']
                    dt['offset'] = code_data[code_index]['Offset']
                }
                component_code_rebase_dialog.create(dt)
                break
        }
    }

    codelist.on_save_clicked = function(ele) {
        ons.createElement('code_save', { append: true }).then(function(popover) {
            var fname = component_codelist_file.file === '_null' ? '' : component_codelist_file.file
            $(popover).find('input[name="save_file"]').val(fname)
            $(popover).find('input[name="save_file"]').bind('input', (event) => {
                if (event.target.value.length > 0) {
                    $(popover).find('ons-button[name="save_button"]').removeAttr('disabled')
                } else {
                    $(popover).find('ons-button[name="save_button"]').attr('disabled', 'disabled')
                }
            })
            $(popover).find('ons-button[name="cancel_button"]').bind('click', (event) => {popover.hide()})

            if (fname.length == 0) {
                $(popover).find('ons-button[name="save_button"]').attr('disabled', 'disabled')
            }
            $(popover).find('ons-button[name="save_button"]').bind('click', (event) => {
                var file = $(popover).find('input[name="save_file"]').val()
                $.send('/codelist', { 'command': "CODELIST_SAVE", 'file': file}, on_codelist_status);
                popover.hide()
            })


            popover.show("#"+"codelist_save_button");
        });
    }

    codelist.on_download_clicked = function(ele) {
        component_codelist_download.obj.attr('disabled', 'disabled')
        var name = component_codelist_file.file
        if (name === '_null') {
            name = 'unknown_codelist'
        }
        $.ajax({
            type: "GET",
            url: '/codelist',
            data: { "name": name },
            xhrFields: {
                responseType: 'blob' // to avoid binary data being mangled on charset conversion
            },
            success: function(blob, status, xhr) {
                // check for a filename
                var filename = "";
                var disposition = xhr.getResponseHeader('Content-Disposition');
                if (disposition && disposition.indexOf('attachment') !== -1) {
                    var filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                    var matches = filenameRegex.exec(disposition);
                    if (matches != null && matches[1]) filename = matches[1].replace(/['"]/g, '');
                }

                if (typeof window.navigator.msSaveBlob !== 'undefined') {
                    // IE workaround for "HTML7007: One or more blob URLs were revoked by closing the blob for which they were created. These URLs will no longer resolve as the data backing the URL has been freed."
                    window.navigator.msSaveBlob(blob, filename);
                } else {
                    var URL = window.URL || window.webkitURL;
                    var downloadUrl = URL.createObjectURL(blob);

                    if (filename) {
                        // use HTML5 a[download] attribute to specify filename
                        var a = document.createElement("a");
                        // safari doesn't support this yet
                        if (typeof a.download === 'undefined') {
                            window.location.href = downloadUrl;
                        } else {
                            a.href = downloadUrl;
                            a.download = filename;
                            document.body.appendChild(a);
                            a.click();
                        }
                    } else {
                        window.location.href = downloadUrl;
                    }

                    setTimeout(function () { URL.revokeObjectURL(downloadUrl); component_codelist_download.obj.removeAttr('disabled') }, 100); // cleanup
                }
            }
        });
    }

    codelist.on_upload_clicked = function(file) {
        $('#codelist_upload_button').val("");
        if (file.size > 600000) {
            ons.notification.toast('File must be under 600KB', { timeout: 2000, animation: 'fall' })
            return
        } else if (file.size <= 20) {
            ons.notification.toast('Codelist file is too small.', { timeout: 2000, animation: 'fall' })
            return
        }
        var reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = function(event) {
            var result = event.target.result;
            var fileName = file.name;
            $.post('/codelist', { "command": "CODELIST_UPLOAD", data: result, name: fileName }, on_codelist_status);
        }
    }

    codelist.on_delete_clicked = function(ele) {
        ons.createElement('delete_code_file', { append: true }).then(function(dialog) {
            $(dialog).find('#delete_code_file_name').text(component_codelist_file.file)
            $(dialog).find('ons-alert-dialog-button[name="cancel_button"]').bind('click', () => {dialog.hide()})
            $(dialog).find('ons-alert-dialog-button[name="delete_button"]').bind('click', () => {
                $.send('/codelist', { 'command': "CODELIST_DELETE_LIST", 'file': component_codelist_file.file}, on_codelist_status);
                dialog.hide()
            })
            dialog.show();
        });
    }

    codelist.on_add_clicked = function(ele) {
        component_code_dialog.create({})
    }

    codelist.get_dialog = function() {
        return component_code_dialog
    }

    codelist.get_rebase_dialog = function() {
        return component_code_rebase_dialog
    }


    codelist.address_copy = function(index) {
        var source = code_data[index]['Source']
        if (source === 'address') {
            document.clipboard.copy({'address': code_data[index]['Address'], 'value': value_map[index]})
        } else {
            document.clipboard.copy({'address': aob_resolve_map[index]['Addresses'][0], 'value': value_map[index]})
        }
    }

    codelist.copy_code = function(index, element) {
        var source = code_data[index]['Source']
        var data;
        event.stopPropagation()
        if (source === 'address') {
            data = {'address': code_data[index]['Address'], 'value': value_map[index]}
        } else if (source === 'pointer') {
            data = {'address': code_data[index]['Address'], 'value': value_map[index], 'offsets': code_data[index]['Offsets']}
            if (has(pointer_resolve_map, index.toString())) {
                data['resolved'] = pointer_resolve_map[index]
            }
        } else {
            var selected = has(code_data[index], 'Selected') && code_data[index].Selected >=0 ? code_data[index].Selected : -1
            if (selected >= 0) {
                data = {'address': aob_resolve_map[index]['Addresses'][selected], 'value': value_map[index], 'aob': code_data[index]['AOB'], 'offset': code_data[index]['Offset']}
            } else {
                if (aob_resolve_map[index].hasOwnProperty('Addresses') && aob_resolve_map[index]['Addresses'].length > 0) {
                    data = {'address': aob_resolve_map[index]['Addresses'][0], 'value': value_map[index], 'aob': code_data[index]['AOB'], 'offset': code_data[index]['Offset']}
                } else {
                    data = {'aob': code_data[index]['AOB'], 'offset': code_data[index]['Offset']}
                }
            }
            if (aob_resolve_map[index].hasOwnProperty('LastAddresses') && aob_resolve_map[index]['LastAddresses'].length > 0) {
                data['last_addresses'] = aob_resolve_map[index]['LastAddresses']
            }
        }
        document.clipboard.copy(data)
    }


    codelist.clipboard_data_copied = function(data) {
        if (sel_codelist_process.val() !== '_null') {
            btn_paste_code[0].show()
        }
    }

    codelist.clipboard_data_pasted = function(data,  desc) {
        var type = ''
        var address = ''
        if (has(data, 'offsets')) { //this will be a pointer
            type = 'pointer'
            address = has(data, 'address') ? data.address : data.base_address
        } else if (has(data, 'aob')) { //must be an aob
            type = 'aob'
            address = 0
        } else { //an address
            type = 'address'
            address = has(data, 'address') ? data.address : data.base_address
        }
        var cmd = { 'command': "CODELIST_ADD_CODE", 'type': type,
                              'address': address,
                              'aob': has(data, 'aob') ? data.aob : 0,
                              'offset': has(data, 'offset') ? data.offset : 0,
                              'offsets': has(data, 'offsets') ? data.offsets : 0
                              }
        $.send('/codelist', cmd, on_codelist_status);
    }

    codelist.clipboard_data_cleared = function() {
        btn_paste_code[0].hide()

    }


    //Private Methods
    function on_codelist_ready() {
        $.send('/codelist', { 'command': "CODELIST_GET"}, on_codelist_status);
    }

    function on_codelist_status(result) {
        if (has(result, 'file_data')) {
            code_data = result.file_data
            component_code_list.empty()
            if (result.file_data === null) {
                code_list = undefined
                code_data = {}
            } else {
                code_list = component_code_list
                code_list.setup(result, code_list)
                code_list.obj = $('#code_list')
                apply_events(code_list)
            }
        } else if (code_list !== undefined) {
            code_list.setup(result, code_list)
        }
        component_codelist_file_row.setup(result, component_codelist_file_row)

        if (has(result, 'error')) {
            ons.notification.toast(result.error, { timeout: 4000, animation: 'fall' })
        }
        if (has(result, 'repeat') && result.repeat > 0) {
            if (codelist.updater !== undefined) {
                clearTimeout(codelist.updater);
            }
            codelist.updater = setTimeout(()=>{$.send('/codelist', { "command": "CODELIST_STATUS" }, on_codelist_status);}, result.repeat)
        }
    }

    var component_codelist_file_row = {
        'id': "row_codelist_loadsave",
        'obj': undefined,
        'setup': (result, _this) => {
            if (component_codelist_file.obj === undefined) {
                component_codelist_file.obj = $('#'+component_codelist_file.id)
            }
            if (component_codelist_save.obj === undefined) {
                component_codelist_save.obj = $('#'+component_codelist_save.id)
            }
            if (component_codelist_download.obj === undefined) {
                component_codelist_download.obj = $('#'+component_codelist_download.id)
            }
            if (component_codelist_upload.obj === undefined) {
                component_codelist_upload.obj = $('#'+component_codelist_upload.id)
            }
            if (component_codelist_delete.obj === undefined) {
                component_codelist_delete.obj = $('#'+component_codelist_delete.id)
            }
            component_codelist_file.setup(result, component_codelist_file)
            component_codelist_save.setup(result, component_codelist_save)
            component_codelist_download.setup(result, component_codelist_download)
            component_codelist_upload.setup(result, component_codelist_upload)
            component_codelist_delete.setup(result, component_codelist_delete)
        },
        'update': (_this) => {}
    }

    var component_codelist_save = {
        'id': "codelist_save_button",
        'obj': undefined,
        'setup': (result, _this) => {
            if (code_list && code_list.children.length > 0) {
                _this.obj.removeAttr('disabled')
            } else {
                _this.obj.attr('disabled', 'disabled')
            }
        },
        'update': (_this) => {}
    }

    var component_codelist_download = {
        'id': "codelist_download_button",
        'obj': undefined,
        'setup': (result, _this) => {
            if (code_list && code_list.children.length > 0) {
                _this.obj.removeAttr('disabled')
            } else {
                _this.obj.attr('disabled', 'disabled')
            }
        },
        'update': (_this) => {}
    }

    var component_codelist_upload = {
        'id': "codelist_upload_button",
        'obj': undefined,
        'setup': (result, _this) => {
                _this.obj.removeAttr('disabled')
        },
        'update': (_this) => {}
    }

    var component_codelist_delete = {
        'id': "codelist_delete_button",
        'obj': undefined,
        'setup': (result, _this) => {
            if (code_list && code_list.children.length > 0 && component_codelist_file.file !== '_null') {
                _this.obj.removeAttr('disabled')
            } else {
                _this.obj.attr('disabled', 'disabled')
            }
        },
        'update': (_this) => {}
    }

    var component_codelist_file = {
        'id': "codelist_file_selection",
        'obj': undefined,
        'setup': (result, _this) => {
            if (has(result, 'files')) {
                _this['files'] = result.files;
                _this.obj.find('option[value != "_null"]').remove();
                _this.files.forEach((item, index) => {
                    _this.obj.find('option:first').after($('<option>', {value: item, text: item}))
                });
            }
            if (has(result, 'file')) {
                _this['file'] = result.file;
                _this.obj.val(_this['file'])
            }
        },
        'changed': (_this) => {
            $.send('/codelist', { "command": "CODELIST_LOAD", 'file': _this.obj.val() }, on_codelist_status);
            _this.update(_this)
        },
        'in': (name) => {return _this.files.includes(name);},
        'files': [],
        'file': "_null",
        'update': (_this) => {
        }
    }

    var component_code_list = {
        'id': "code_list",
        'obj': undefined,
        'setup': (result, _this) => {
            if (has(result, 'file_data')) {
                _this.children = []
                $.each(result.file_data, ( index, item ) => {
                    var head = component_code_header.create(index, result.file_data[index])
                    var comp = component_code.create(index, result.file_data[index])
                    _this.children.push([head, comp])
                    _this.obj.append(head.obj)
                    _this.obj.append(comp.obj)
                    head.setup(item, head)
                    comp.setup(item, comp)
                });
            }
            if (has(result, 'results')) {
                aob_resolve_map = {}
                pointer_resolve_map = {}
                value_map = {}
                $.each(result.results, ( id, res ) => {
                    var index = _this.children.findIndex((item) => {return item[0].id == component_code_header.id+id})
                    _this.children[index][0].setup(res, _this.children[index][0])
                    _this.children[index][1].setup(res, _this.children[index][1])
                });
            }
            else if (has(result, 'remove_index')) {
                var id = result.remove_index
                var index = _this.children.findIndex((item) => {return item[0].id == component_code_header.id+id})
                _this.children[index][0].obj.remove()
                _this.children[index][1].obj.remove()
                _this.children.splice(index, 1)
            }
            else if (has(result, 'new_code')) {
                var code = result.new_code
                var head = component_code_header.create(result.index, code)
                var comp = component_code.create(result.index, code)
                _this.children.push([head, comp])
                _this.obj.append(head.obj)
                _this.obj.append(comp.obj)
                code_data[result.index] = code
                head.setup(code, head)
                comp.setup(code, comp)
                apply_events(head)
                apply_events(comp)
            }
            else if (has(result, 'edit_code')) {
                var code = result.edit_code
                var id = result.index
                var index = _this.children.findIndex((item) => {return item[0].id == component_code_header.id+id})
                var pos = _this.obj.children().index(_this.children[index][0].obj)
                _this.children[index][0].obj.remove()
                _this.children[index][1].obj.remove()
                _this.children.splice(index, 1)
                var head = component_code_header.create(result.index, code)
                var comp = component_code.create(result.index, code)
                _this.children.push([head, comp])
                _this.obj.insertAt(pos, head.obj)
                _this.obj.insertAt(pos+1, comp.obj)
                code_data[result.index] = code
                apply_events(head)
                apply_events(comp)
                head.setup(code, head)
                comp.setup(code, comp)
            }
            else if (has(result, 'changes')) {
                var codes = result.changes
                $.each(codes, function(i, value ){
                    var code = value[1]
                    var id = value[0]
                    var index = _this.children.findIndex((item) => {return item[0].id == component_code_header.id+id})
                    var pos = _this.obj.children().index(_this.children[index][0].obj)
                    _this.children[index][0].obj.remove()
                    _this.children[index][1].obj.remove()
                    _this.children.splice(index, 1)
                    var head = component_code_header.create(id, code)
                    var comp = component_code.create(id, code)
                    _this.children.push([head, comp])
                    _this.obj.insertAt(pos, head.obj)
                    _this.obj.insertAt(pos+1, comp.obj)
                    code_data[id] = code
                    apply_events(head)
                    apply_events(comp)
                    head.setup(code, head)
                    comp.setup(code, comp)
                });
            }
        },
        'update': (_this) => {},
        'template': '<ons-list id="code_list">##code_components##</ons-list>',
        'empty': () => {
            $('#code_list').empty()
            component_code_list.obj = $('#code_list')
            while (component_code_list.children.length) { component_code_list.children.pop(); }
        },
        'children': []
    }

    var component_code_header = {
        'id': 'code_header_',
        'obj': undefined,
        'index': -1,
        'name_component': {},
        'setup': (result, _this) => {
            _this.children.forEach( (item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {},
        'template': '<ons-list-header id="##id##" style="background-color:#ddd; padding:0px 5px ;"></ons-list-header>',
        'create': (index, data) => {
            var t = {...component_code_header};
            t.id = component_code_header.id+index
            t.index = index
            t.template = component_code_header.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            //create the elements
            t.children = []
            t.children.push(component_row_name.create(index))
            t.children.forEach((item, index) =>{
                t.obj.append(item.obj)
            })
            return t;
        },
        'children': []
    }

    var component_code = {
        'id': 'code_item_',
        'obj': undefined,
        'index': -1,
        'name_component': {},
        'setup': (result, _this) => {
            _this.children.forEach( (item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {},
        'template': '<ons-list-item id="##id##" modifier="longdivider" expandable><div name="expand" class="expandable-content"></div></ons-list-item>',
        'create': (index, data) => {
            var t = {...component_code};
            t.id = component_code.id+index
            t.index = index
            t.template = component_code.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            //create the elements
            t.children = []
            t.children.push(component_row_value.create(index))
            if (data.Source == 'address') {
                t.children.push(component_row_address.create(index))
            } else if (data.Source == 'pointer') {
                t.children.push(component_row_address.create(index))
                t.children.push(component_row_offsets.create(index))
            } else {
                t.children.push(component_row_aob.create(index))
                t.children.push(component_row_offset.create(index))
            }
            t.children.forEach((item, index) =>{
                if (index == 0) {
                    t.obj.find('.center').append(item.obj)
                } else {
                    t.obj.find('div[name="expand"]').append(item.obj)
                }
            })
            t.obj.find('div.top > div.center').css('max-height', '32px')
            t.obj.find('div.top > div.center').css('min-height', '8px')
            t.obj.find('div.top > div.center').css('align-content', 'center')
            t.obj.find('div.top > div.right').css('max-height', '32px')
            t.obj.find('div.top > div.right').css('min-height', '8px')
            t.obj.find('div.top > div.right').css('align-content', 'center')
            return t;
        },
        'children': []
    }

    var component_row_name = {
        'id': 'row_name_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            _this.children.forEach((item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {},
        'template': `<ons-row id="##id##" style="margin-bottom:10px; margin-top:0px;">
                        <ons-col align="center" width="75%" class="col ons-col-inner">
                        </ons-col>
                        <ons-col align="center" width="10%" class="col ons-col-inner">
                        </ons-col>
                    </ons-row>`,
        'create': (index) => {
            var t = {...component_row_name};
            t.id = component_row_name.id+index
            t.index = index
            t.template = component_row_name.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            var cc_name = component_code_name.create(index)
            t.obj.find('ons-col').eq(0).append(cc_name.obj)
            var cc_options = component_code_options.create(index)
            t.obj.find('ons-col').eq(1).append(cc_options.obj)
            t.children = [cc_name, cc_options]
            return t;
        },
        'children': []
    }
    var component_code_name = {
        'id': 'code_component_name_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Name')) {
                _this.obj.val(result.Name)
            }
        },
        'update': (_this) => {},
        'template': '<input tabIndex="-1" type="text" id="##id##" name="code_address" class="text-input text-input--material text-full" onkeydown="codelist.code_name_changed(false, this, ##index##)" onblur="codelist.code_name_changed(true, this, ##index##)" value="Name" autocomplete="chrome-off" autocapitalize="off" style="font-weight: bold;">',
        'create': index => {
            var t = {...component_code_name};
            t.id = component_code_name.id+index
            t.index = index
            t.template = component_code_name.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            t.obj.bind('click', 'input[type=text]', function(){
                if (this.value.startsWith('Code #')) {
                    this.select()
                }
                event.stopPropagation()
            })
            return t;
        }
    }
    var component_code_options = {
        'id': 'code_menu_button_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
        },
        'update': (_this) => {},
        'template': '<button class="tp" onclick="codelist.code_menu_clicked(this, ##index##)" id="##id##"><div class="navigation"></div>',
        'create': (index, position) => {
            var t = {...component_code_options};
            t.id = component_code_options.id+index
            t.index = index
            t.template = component_code_options.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }

    var component_row_value = {
        'id': 'row_value_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            _this.children.forEach((item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {},
        'template': `<ons-row id="##id##">
                        <ons-col align="center" width="22%" class="col ons-col-inner">
                        </ons-col>
                        <ons-col align="center" width="54%" class="col ons-col-inner">
                        </ons-col>
                        <ons-col class="checkbox--grid" align="right" width="7%" class="col ons-col-inner">
                        </ons-col>
                        <ons-col align="right" width="12%" class="col ons-col-inner">
                        </ons-col>
                    </ons-row>`,
        'create': index => {
            var t = {...component_row_value};
            t.id = component_row_value.id+index
            t.index = index
            t.template = component_row_value.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            var cc_size = component_code_size.create(index)
            t.obj.find('ons-col').eq(0).append(cc_size.obj)
            var cc_value = component_code_value.create(index)
            t.obj.find('ons-col').eq(1).append(cc_value.obj)
            var cc_freeze = component_code_freeze.create(index)
            t.obj.find('ons-col').eq(2).append(cc_freeze.obj)
            var cc_copy = component_code_copy.create(index)
            t.obj.find('ons-col').eq(3).append(cc_copy.obj)
            t.children = [cc_size, cc_value, cc_freeze, cc_copy]
            return t;
        },
        'children': []
    }
    var component_code_size = {
        'id': 'code_component_size_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Type')) {
                _this.obj.val(result.Type)
            }
        },
        'update': (_this) => {},
        'template': `<select name="code_size" id="##id##" class="select-input select-input--material" onchange="codelist.code_size_changed(this, ##index##)">
                        <option value="byte_1">BYTE</option>
                        <option value="byte_2">2 BYTES</option>
                        <option value="byte_4" selected>4 BYTES</option>
                        <option value="byte_8">8 BYTES</option>
                        <option value="float">FLOAT</option>
                     </select>`,
        'create': index => {
            var t = {...component_code_size};
            t.id = component_code_size.id+index
            t.index = index
            t.template = component_code_size.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            t.obj.bind('click', function() {event.stopPropagation();})
            return t;
        }
    }
    var component_code_value = {
        'id': 'code_component_value_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Value')) {
                value_map[_this.index] = result.Value
                if ($(":focus")[0] && $(":focus")[0].id === _this.obj[0].id){
                    return
                }
                _this.obj.val(result.Value.Display)
                if (result.Value.Display.startsWith('?')) {
                    _this.obj.attr('disabled', 'disabled')
                } else {
                    _this.obj.removeAttr('disabled')
                }
            }
        },
        'update': (_this) => {},
        'template': '<input tabIndex="-1" inputmode="decimal" autocomplete="chrome-off" type="text" id="##id##" name="code_value" class="text-input text-input--material text-full r-value" onkeydown="codelist.code_value_changed(false, this, ##index##)" onblur="codelist.code_value_changed(true, this, ##index##)">',
        'create': index => {
            var t = {...component_code_value};
            t.id = component_code_value.id+index
            t.index = index
            t.template = component_code_value.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            t.obj.bind('click', 'input[type=text]', function(){ this.select(); event.stopPropagation() })
            return t;
        }
    }
    var component_code_freeze = {
        'id': 'code_component_freeze_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Freeze')) {
                _this.obj.parent().find('input').prop("checked", result.Freeze)
            }
            if (has(result, 'Value')) {
                if (result.Value == '??' && !_this.obj.parent().find('input').prop("checked")) {
                    _this.obj.parent().find('input').attr('disabled', 'disabled')
                } else if (result.Value != '??' && _this.obj.parent().find('input').prop('disabled')) {
                    _this.obj.parent().find('input').removeAttr('disabled')
                }

            }

        },
        'update': (_this) => {},
        'template': '<label class="checkbox checkbox--material"><input tabIndex="-1" id="##id##" type="checkbox" class="checkbox__input checkbox--material__input" onchange="codelist.code_freeze_changed(this, ##index##)"> <div class="checkbox__checkmark checkbox--material__checkmark"></div>',
        'create': index => {
            var t = {...component_code_freeze};
            t.id = component_code_freeze.id+index
            t.index = index
            t.template = component_code_freeze.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            t.obj.bind('click', function() {event.stopPropagation();})
            return t;
        }
    }
    var component_code_copy = {
        'id': 'code_component_copy_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {

        },
        'update': (_this) => {},
        'template': '<ons-button modifier="quiet" name="add_button" data-address="##address##" onclick="codelist.copy_code(##index##, this)"><ons-icon icon="md-copy"></ons-icon></ons-button>',
        'create': index => {
            var t = {...component_code_copy};
            t.id = component_code_copy.id+index
            t.index = index
            t.template = component_code_copy.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }

    var component_row_address = {
        'id': 'row_address_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            _this.children.forEach((item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {},
        'template': `<ons-row id="##id##">
                        <ons-col align="center" width="20%" class="col ons-col-inner">
                            Address:
                        </ons-col>
                        <ons-col align="center" width="60%" class="col ons-col-inner">
                        </ons-col>
                    </ons-row>`,
        'create': index => {
            var t = {...component_row_address};
            t.id = component_row_address.id+index
            t.index = index
            t.template = component_row_address.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            var cc_address = component_code_address.create(index)
            t.obj.find('ons-col').eq(1).append(cc_address.obj)
            t.children = [cc_address]
            return t;
        },
        'children': []
    }
    var component_code_address = {
        'id': 'code_component_address_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Address')) {
                if (result.Address.indexOf(':') >= 0) {
                    _this.obj.val(result.Address.toString())
                }  else {
                    _this.obj.val(result.Address.toString(16).toUpperCase())
                }
            }
        },
        'update': (_this) => {},
        'template': '<input tabIndex="-1" type="text" id="##id##" name="code_address" class="text-input text-input--material text-full r-value" oninput="codelist.address_value_changed(this)" readonly>',
        'create': index => {
            var t = {...component_code_address};
            t.id = component_code_address.id+index
            t.index = index
            t.template = component_code_address.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }

    var component_row_aob = {
        'id': 'row_aob_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            _this.children.forEach((item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {},
        'template': `<ons-row id="##id##">
                        <ons-col align="center" width="20%" class="col ons-col-inner">
                            AOB:
                        </ons-col>
                        <ons-col align="center" width="60%" class="col ons-col-inner">
                        </ons-col>
                        <ons-col align="center" width="20%" class="col ons-col-inner">
                        </ons-col>
                    </ons-row>`,
        'create': index => {
            var t = {...component_row_aob};
            t.id = component_row_aob.id+index
            t.index = index
            t.template = component_row_aob.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            var cc_aob = component_code_aob.create(index)
            t.obj.find('ons-col').eq(1).append(cc_aob.obj)
            var cc_aob_address_copy = component_copy_aob_address.create(index)
            t.obj.find('ons-col').eq(2).append(cc_aob_address_copy.obj)
            t.children = [cc_aob, cc_aob_address_copy]
            return t;
        },
        'children': []
    }
    var component_code_aob = {
        'id': 'code_component_aob_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'AOB')) {
                _this.obj.val(result.AOB)
            }
        },
        'update': (_this) => {},
        'template': '<input tabIndex="-1" type="text" id="##id##" name="code_address" class="text-input text-input--material text-full r-value" oninput="codelist.aob_value_changed(this)" readonly>',
        'create': index => {
            var t = {...component_code_aob};
            t.id = component_code_aob.id+index
            t.index = index
            t.template = component_code_aob.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }

    var component_copy_aob_address = {
        'id': 'code_component_copy_aob_address_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, "Addresses") && result.Addresses !== null && result.Addresses.length > 0) {
                _this.obj.show()
            } else {
                _this.obj.hide()
            }
        },
        'update': (_this) => {},
        'template': '<ons-button id="##id##" modifier="material--flat" onclick="codelist.address_copy(##index##)"><ons-icon style="color:#777;" size="26px" icon="md-copy"></ons-icon></ons-button>',
        'create': index => {
            var t = {...component_copy_aob_address};
            t.id = component_copy_aob_address.id+index
            t.index = index
            t.template = component_copy_aob_address.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }

    var component_row_offset = {
        'id': 'row_offset_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            _this.children.forEach((item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {},
        'template': `<ons-row id="##id##">
                        <ons-col align="center" width="20%" class="col ons-col-inner">
                            Offset:
                        </ons-col>
                        <ons-col align="center" width="25%" class="col ons-col-inner" name="offset_refresh">
                            <ons-row>
                                <ons-col align="center" class="col ons-col-inner" name="first">
                                </ons-col>
                            </ons-row>
                            <ons-row>
                                <ons-col align="center" class="col ons-col-inner" name="second">
                                </ons-col>
                            </ons-row>
                        </ons-col>
                        <ons-col align="center" width="55%" class="col ons-col-inner" name="addresses">
                        </ons-col>
                    </ons-row>`,
        'create': index => {
            var t = {...component_row_offset};
            t.id = component_row_offset.id+index
            t.index = index
            t.template = component_row_offset.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            var cc_offset = component_code_offset.create(index)
            var cc_offset_address = component_code_offset_address.create(index)
            var cc_offset_refresh = component_code_offset_refresh.create(index)

            t.obj.find('ons-col[name="offset_refresh"]').find('ons-col').eq(0).append(cc_offset.obj)
            t.obj.find('ons-col[name="offset_refresh"]').find('ons-col').eq(1).append(cc_offset_refresh.obj)
            t.obj.find('ons-col[name="addresses"]').append(cc_offset_address.obj)

            t.children = [cc_offset, cc_offset_address, cc_offset_refresh]
            return t;
        },
        'children': []
    }
    var component_code_offset = {
        'id': 'code_component_offset_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Offset')) {
                _this.obj.val(result.Offset)
            }
        },
        'update': (_this) => {},
        'template': '<input tabIndex="-1" type="text" id="##id##" name="code_address" class="text-input text-input--material text-full" oninput="codelist.offset_value_changed(this)" readonly>',
        'create': index => {
            var t = {...component_code_offset};
            t.id = component_code_offset.id+index
            t.index = index
            t.template = component_code_offset.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }
    var component_code_offset_address = {
        'id': 'code_component_offset_addresses_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'LastAddresses')) {
                if (!aob_resolve_map.hasOwnProperty(_this.index)) {
                    aob_resolve_map[_this.index] = {}
                }
                aob_resolve_map[_this.index]['LastAddresses'] = result.LastAddresses
            }
            if (has(result, 'Addresses')) {
                if (!aob_resolve_map.hasOwnProperty(_this.index)) {
                    aob_resolve_map[_this.index] = {}
                }
                if (result.Addresses.Display.length > 0) {
                    aob_resolve_map[_this.index]['Addresses'] = result.Addresses.Display
                    if ($(":focus")[0] && $(":focus")[0].id === _this.obj[0].id){
                        return
                    }
                    _this.obj.empty()
                    result.Addresses.Display.forEach((item, index) =>{
                        _this.obj.append($('<option>', {
                            value: item,
                            text: item
                        }));
                    })
                }
            }
        },
        'update': (_this) => {},
        'template': '<select id=##id## size="3" style="min-width:100px;"></select>',
        'changed': (_this) => {
            _this.selected = _this.obj.prop('selectedIndex')
            $.send('/codelist', {'command': 'CODELIST_AOB_SELECT', 'index': _this.index, 'selected': _this.selected, 'select_index': _this.obj.prop('selectedIndex')}, () => {
                code_data[_this.index]['Selected'] = _this.selected
            })
        },
        'create': index => {
            var t = {...component_code_offset_address};
            t.id = component_code_offset_address.id+index
            t.index = index
            t.template = component_code_offset_address.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        },
        'selected': '_null'
    }
    var component_code_offset_refresh = {
        'id': 'code_component_offset_refresh_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
        },
        'update': (_this) => {},
        'template': '<ons-button modifier="quiet" id="##id##" onclick="codelist.on_refresh(this, ##index##)">Refresh</ons-button>',
        'create': index => {
            var t = {...component_code_offset_refresh};
            t.id = component_code_offset_refresh.id+index
            t.index = index
            t.template = component_code_offset_refresh.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }

    var component_row_offsets = {
        'id': 'row_offsets_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            _this.children.forEach((item, index) => {
                item.setup(result, item)
            })
        },
        'update': (_this) => {},
        'template': `<ons-row id="##id##">
                        <ons-row>
                            <ons-col align="center" width="20%" class="col ons-col-inner">
                                Offsets:
                            </ons-col>
                            <ons-col align="center" width="45%" class="col ons-col-inner" name="pointer_offsets">
                            </ons-col>
                        </ons-row>
                        <ons-row>
                            <ons-col align="center" width="20%" class="col ons-col-inner">
                                Resolved:
                            </ons-col>
                            <ons-col align="center" width="45%" class="col ons-col-inner" name="pointer_address">
                            </ons-col>
                        </ons-row>
                    </ons-row>`,
        'create': index => {
            var t = {...component_row_offsets};
            t.id = component_row_offsets.id+index
            t.index = index
            t.template = component_row_offsets.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            var cc_offsets = component_code_offsets.create(index)
            var cc_offsets_address = component_code_offsets_address.create(index)
            t.obj.find('ons-col[name="pointer_offsets"]').append(cc_offsets.obj)
            t.obj.find('ons-col[name="pointer_address"]').append(cc_offsets_address.obj)
            t.children = [cc_offsets, cc_offsets_address]
            return t;
        },
        'children': []
    }
    var component_code_offsets = {
        'id': 'code_component_offsets_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Offsets')) {
                _this.obj.val(result.Offsets)
            }
        },
        'update': (_this) => {},
        'template': '<input tabIndex="-1" type="text" id="##id##" name="code_address" class="text-input text-input--material text-full" oninput="codelist.offset_value_changed(this)" readonly>',
        'create': index => {
            var t = {...component_code_offsets};
            t.id = component_code_offsets.id+index
            t.index = index
            t.template = component_code_offsets.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }
    var component_code_offsets_address = {
        'id': 'code_component_offsets_address_',
        'obj': undefined,
        'index': -1,
        'setup': (result, _this) => {
            if (has(result, 'Resolved')) {
                pointer_resolve_map[_this.index] = result.Resolved.Display
                _this.obj.val(result.Resolved.Display)
            }
        },
        'update': (_this) => {},
        'template': '<input tabIndex="-1" type="text" id="##id##" name="code_address" class="text-input text-input--material text-full" oninput="codelist.offset_value_changed(this)" readonly>',
        'create': index => {
            var t = {...component_code_offsets_address};
            t.id = component_code_offsets_address.id+index
            t.index = index
            t.template = component_code_offsets_address.template.replaceAll("##index##", index).replaceAll('##id##', t.id)
            t.obj = $(ons.createElement(t.template))
            return t;
        }
    }


    var component_code_dialog = {
        'id': 'add_code_dialog',
        'obj': undefined,
        'setup': (result, _this) => {
        },
        'update': (_this) => {},
        'setup': (data) => {
            if (has(data, 'title')) {
                component_code_dialog.obj.find('p').text(data.title)
            } else {
                component_code_dialog.obj.find('p').text('Add Code')
            }
            if (has(data, 'index')) {
                component_code_dialog.index = data.index
                $("#add_code_button").text('Ok')
            } else {
                component_code_dialog.index = -1
                $("#add_code_button").text('Add')
            }
            $("#add_code_address").val('')
            $("#add_code_aob").val('')
            $("#add_code_offset").val('')
            $("#add_code_offsets").val('')
            if (has(data, 'address')) {
                $("#add_code_type").val('address')
                $("#add_code_address").val(data.address)
                $("#add_code_address").parents("ons-row").show()
                $("#add_code_aob").parents("ons-row").hide()
                $("#add_code_offset").parents("ons-row").hide()
                $("#add_code_offsets").parents("ons-row").hide()
            } else if (has(data, 'aob')) {
                $("#add_code_type").val('aob')
                $("#add_code_aob").val(data.aob)
                $("#add_code_offset").val(data.offset)
                $("#add_code_address").parents("ons-row").hide()
                $("#add_code_aob").parents("ons-row").show()
                $("#add_code_offset").parents("ons-row").show()
                $("#add_code_offsets").parents("ons-row").hide()
            } else if (has(data, 'pointer')) {
                $("#add_code_type").val('pointer')
                $("#add_code_address").val(data.pointer)
                $("#add_code_offsets").val(data.offsets)
                $("#add_code_address").parents("ons-row").show()
                $("#add_code_offsets").parents("ons-row").show()
                $("#add_code_aob").parents("ons-row").hide()
                $("#add_code_offset").parents("ons-row").hide()
            } else {
                $("#add_code_type").val('address')
                $("#add_code_aob").parents("ons-row").hide()
                $("#add_code_offset").parents("ons-row").hide()
                $("#add_code_offsets").parents("ons-row").hide()
                $("#add_code_address").parents("ons-row").show()
            }
            component_code_dialog.validate()
        },
        'create': (data) => {
            if (component_code_dialog.obj === undefined) {
                ons.createElement('add_code', { append: true })
                .then(function(dialog) {
                    component_code_dialog.obj = $(dialog)
                    component_code_dialog.setup(data)
                    dialog.show();
                });
            } else {
                component_code_dialog.setup(data)
                component_code_dialog.obj[0].show()
            }
        },
        'type_changed': () => {
            if ($("#add_code_type").val() === 'address') {
                $("#add_code_aob").parents("ons-row").hide()
                $("#add_code_offset").parents("ons-row").hide()
                $("#add_code_address").parents("ons-row").show()
                $("#add_code_offsets").parents("ons-row").hide()
            } else if ($("#add_code_type").val() === 'aob') {
                $("#add_code_address").parents("ons-row").hide()
                $("#add_code_aob").parents("ons-row").show()
                $("#add_code_offset").parents("ons-row").show()
                $("#add_code_offsets").parents("ons-row").hide()
            } else if ($("#add_code_type").val() === 'pointer') {
                $("#add_code_address").parents("ons-row").show()
                $("#add_code_aob").parents("ons-row").hide()
                $("#add_code_offset").parents("ons-row").hide()
                $("#add_code_offsets").parents("ons-row").show()
            }
            component_code_dialog.validate()
        },
        'index': -1,
        'validate': () => {
            if ($("#add_code_type").val() === 'address') {
                var addr = $("#add_code_address").val()
                if ((/^(?!.{256,})(?!(aux|clock\$|con|nul|prn|com[1-9]|lpt[1-9])(?:$|\.))[^ ][ \.\w-$()+=[\];#@~,&amp;']+[^\. ]:\d+\+[0-9a-f]+$/i.test(addr)) || /^[0-9A-F]{5,16}$/i.test(addr)) {
                    $("#add_code_button").removeAttr('disabled')
                } else {
                    $("#add_code_button").attr('disabled', 'disabled')
                }
            }
            else if ($("#add_code_type").val() === 'pointer') {
                var addr = $("#add_code_address").val()
                var offsets = $("#add_code_offsets").val()
                if (/^[0-9a-f]+(, ?[0-9a-f]+)*$/i.test(offsets) && ((/^(?!.{256,})(?!(aux|clock\$|con|nul|prn|com[1-9]|lpt[1-9])(?:$|\.))[^ ][ \.\w-$()+=[\];#@~,&amp;']+[^\. ]:\d+\+[0-9a-f]+$/i.test(addr)) || /^[0-9A-F]{5,16}$/i.test(addr))) {
                    $("#add_code_button").removeAttr('disabled')
                } else {
                    $("#add_code_button").attr('disabled', 'disabled')
                }
            } else {
                var aob = $("#add_code_aob").val()
                var offset = $("#add_code_offset").val()
                if (/^(?:([0-9A-F]{2}|\?{2}) )*([0-9A-F]{2}|\?{2})$/i.test(aob) && /^-?[0-9A-F]{1,12}$/i.test(offset)) {
                    $("#add_code_button").removeAttr('disabled')
                } else {
                    $("#add_code_button").attr('disabled', 'disabled')
                }
            }
        },
        'on_cancel': () => {
            component_code_dialog.obj[0].hide()
        },
        'on_add': () => {
            var cmd = { 'command': "CODELIST_ADD_CODE", 'type': $("#add_code_type").val(),
                                  'address': $("#add_code_address").val(), 'aob': $("#add_code_aob").val(),
                                  'offset': $("#add_code_offset").val(), 'offsets': $("#add_code_offsets").val()}
            if (component_code_dialog.index >= 0) {
                cmd['index'] = component_code_dialog.index
            }

            $.send('/codelist', cmd, on_codelist_status);
            component_code_dialog.obj[0].hide()
        }
    }

    var component_code_rebase_dialog = {
        'id': 'rebase_code_dialog',
        'obj': undefined,
        'setup': (result, _this) => {
        },
        'update': (_this) => {},
        'setup': (data) => {
            component_code_rebase_dialog.index = data.index
            component_code_rebase_dialog.type = data.source
            if (document.clipboard.has_aob()) {
                $("#rebase_code_aob_paste_button").show()
            } else {
                $("#rebase_code_aob_paste_button").hide()
            }
            if (document.clipboard.has_address()) {
                $("#rebase_code_address_paste_button").show()
            } else {
                $("#rebase_code_address_paste_button").hide()
            }
            if (document.clipboard.has_pointer()) {
                $("#rebase_code_pointer_paste_button").show()
            } else {
                $("#rebase_code_pointer_paste_button").hide()
            }
            if (has(data, 'address')) {
                $("#rebase_code_address").val(data.address)
                $("#rebase_address").show()
                $("#rebase_pointer").hide()
                $("#rebase_aob").hide()
            } else if (has(data, 'aob')) {
                $("#rebase_code_aob").val(data.aob)
                $("#rebase_code_offset").val(data.offset)
                $("#rebase_address").hide()
                $("#rebase_pointer").hide()
                $("#rebase_aob").show()
            } else if (has(data, 'pointer')) {
                $("#rebase_code_pointer").val(data.pointer)
                $("#rebase_code_offsets").val(data.offsets)
                $("#rebase_address").hide()
                $("#rebase_pointer").show()
                $("#rebase_aob").hide()
            }
            component_code_rebase_dialog.validate()
        },
        'create': (data) => {
            if (component_code_rebase_dialog.obj === undefined) {
                ons.createElement('rebase_code', { append: true })
                .then(function(dialog) {
                    component_code_rebase_dialog.obj = $(dialog)
                    component_code_rebase_dialog.setup(data)
                    dialog.show();
                });
            } else {
                component_code_rebase_dialog.setup(data)
                component_code_rebase_dialog.obj[0].show()
            }
        },
        'index': -1,
        'type': '',
        'validate': () => {
            if (component_code_rebase_dialog.type === 'address') {
                var addr = $("#rebase_code_address").val()
                if ((/^(?!.{256,})(?!(aux|clock\$|con|nul|prn|com[1-9]|lpt[1-9])(?:$|\.))[^ ][ \.\w-$()+=[\];#@~,&amp;']+[^\. ]:\d+\+[0-9a-f]+$/i.test(addr)) || /^[0-9A-F]{5,16}$/i.test(addr)) {
                    $("#rebase_code_button").removeAttr('disabled')
                } else {
                    $("#rebase_code_button").attr('disabled', 'disabled')
                }
            }
            else if (component_code_rebase_dialog.type === 'pointer') {
                var addr = $("#rebase_code_pointer").val()
                var offsets = $("#rebase_code_offsets").val()
                if (/^[0-9a-f]+(, ?[0-9a-f]+)*$/i.test(offsets) && ((/^(?!.{256,})(?!(aux|clock\$|con|nul|prn|com[1-9]|lpt[1-9])(?:$|\.))[^ ][ \.\w-$()+=[\];#@~,&amp;']+[^\. ]:\d+\+[0-9a-f]+$/i.test(addr)) || /^[0-9A-F]{5,16}$/i.test(addr))) {
                    $("#rebase_code_button").removeAttr('disabled')
                } else {
                    $("#rebase_code_button").attr('disabled', 'disabled')
                }
            } else {
                var aob = $("#rebase_code_aob").val()
                var offset = $("#rebase_code_offset").val()
                if (/^(?:([0-9A-F]{2}|\?{2}) )*([0-9A-F]{2}|\?{2})$/i.test(aob) && /^-?[0-9A-F]{1,12}$/i.test(offset)) {
                    $("#rebase_code_button").removeAttr('disabled')
                } else {
                    $("#rebase_code_button").attr('disabled', 'disabled')
                }
            }
        },
        'on_aob_paste': () => {
            if (component_code_rebase_dialog.type == 'aob') {
                $("#rebase_code_aob").val(document.clipboard.data.aob)
                $("#rebase_code_offset").val(document.clipboard.data.offset)
            } else if (component_code_rebase_dialog.type == 'address') {
                $("#rebase_code_address").val(document.clipboard.data.address)
            } else {
                $("#rebase_code_pointer").val(document.clipboard.data.address)
                $("#rebase_code_offsets").val(document.clipboard.data.offsets)
            }
        },
        'on_cancel': () => {
            component_code_rebase_dialog.obj[0].hide()
        },
        'on_rebase': () => {
            var cmd = { 'command': "CODELIST_REBASE_CODE", 'type': component_code_rebase_dialog.type, 'index': component_code_rebase_dialog.index,
                                  'address': (component_code_rebase_dialog.type == 'address' ? $("#rebase_code_address").val() : $("#rebase_code_pointer").val()),
                                  'aob': $("#rebase_code_aob").val(),
                                  'offset': $("#rebase_code_offset").val(), 'offsets': $("#rebase_code_offsets").val()}
            $.send('/codelist', cmd, on_codelist_status)
            component_code_rebase_dialog.obj[0].hide()
        }
    }



    var component_list = [component_codelist_file, component_codelist_save, component_codelist_download, component_codelist_upload, component_codelist_delete, component_code_list]

    function set_process(process_name) {
        sel_codelist_process.val(process_name)
        if (process_name === '_null') {
            process_name = ''
        }
        btn_add_code.removeClass('hide-fab')
        btn_paste_code.removeClass('hide-fab')
        if (process_name.length > 0) {
            div_codelist_block.show()
            btn_add_code[0].show()
            on_codelist_ready()
        } else {
            div_codelist_block.hide()
            btn_add_code[0].hide()
        }


        if (document.clipboard.has_address() || document.clipboard.has_aob()) {
            btn_paste_code[0].show()
        }
        component_code_list.empty()
    }

    function update() {
    }

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

}( window.codelist = window.codelist || {}, jQuery ));
