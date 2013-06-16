var DASH = (function ($) {
    var DASH = {
        articleLists: []
    };

    $(document).ready(function() {
        $('#autorefresh').click(function() {
            if ($(this).is(':checked')){
                DASH.start_reload();
            }
            else {
                DASH.stop_reload();
            }
        });

        $('#add-new-list').click(function () {
            DASH.create_list_menu($(this));
        });

        $('.article-list-row').each(function () {
            DASH.articleLists.push(ArticleList.fromTableRow($(this)));
        });
    });


    DASH.ajax_refresh = function ajax_refresh(div_selector, url, repeat_delay) {
        div_selector = div_selector || '#content';
        url = url || document.URL;
        repeat_delay = repeat_delay || null;
        $(div_selector).load(document.URL + ' ' + div_selector, function(res, status, xhr) {
            if (status !== 'success') {
                clearTimeout(DASH['reload']);
                $('#autorefresh').prop('checked', false);
            } else {
                if (repeat_delay) {
                    if ($('#autorefresh').is(':checked')){
                        DASH['reload'] = setTimeout(function() { ajax_refresh(div_selector, url, repeat_delay); }, repeat_delay);
                    } else {
                        // hmmm, sometimes it doesn't respond to my click... this should stop it
                        clearTimeout(DASH['reload']);
                    }
                }
            }
        });
    };

    DASH.get_refresher = function get_refresher(div_selector, url, repeat_delay) {
        var do_refresh = function do_refresh() {
            return ajax_refresh(div_selector, url, repeat_delay);
        };
    };

    DASH.stop_reload = function stop_reload() {
        clearTimeout(DASH['reload']);
    };

    DASH.start_reload = function start_reload(rate) {
        rate = rate || 221;
        DASH.ajax_refresh('', '', rate);
    };

    DASH.create_list_menu = function create_list_menu($link) {
        function destructMe() {
            $interface.remove();
        }

        function setErr(msg) {
            $interface.find( '.error' ).remove();
            $err = $('<span>', {'class': 'error'}).text(msg);
            $interface.append($err);
        }

        var $interface = $('<div>'),
            $field = $('<input>', {
                type: 'text',
                id: 'create-a-list',
                name: 'list_name'
            }),
            $button = $('<button>', {
                type: 'button',
                id: 'create-list-submit'
            }).text( 'Create!' ),
            $cancel = $('<button>', {
                type: 'cancel',
                id: 'create-list-cancel'
            }).text( 'Cancel' );

        $button.click(function () {
            if ($field.val() === '') {
                setErr('Please enter a list name.');
            } else {
                DASH.create_list($field.val(), destructMe, setErr );
            }
        });

        $cancel.click(destructMe);

        $interface.append(
            $field,
            $button,
            $cancel
        );

        $link.after($interface);
    };

    DASH.create_list = function create_list(name, cb, err) {
        $.ajax(
            '/list_create/' + name,
            {
                method: 'PUT',
                success: function (data) {
                    if (data.error) {
                        err(data.error);
                    } else {
                        DASH.add_new_row(data);
                        cb();
                    }
                }
            }
        );
    };

    DASH.add_new_row = function add_new_row(list) {
        var al = new ArticleList(list.name, list.articles, list.actions, list.date);
        al.buildInterface();
        al.attach($('#in-prog-table'));
        DASH.articleLists.push(al);
    };

    return DASH;
}(jQuery));
