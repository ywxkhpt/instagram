$(function () {
    var oExports = {
        initialize: fInitialize,
        // 渲染更多数据
        renderMore: fRenderMore,
        // 请求数据
        requestData: fRequestData,
        // 简单的模板替换
        tpl: fTpl
    };
    // 初始化页面脚本
    oExports.initialize();

    function fInitialize() {
        var that = this;
        // 常用元素
        that.listEl = $('div.js-image-list');
        // 初始化数据
        that.page = 1;
        that.pageSize = 10;
        that.listHasNext = true;
        // 绑定事件
        $('.js-load-more').on('click', function (oEvent) {
            var oEl = $(oEvent.currentTarget);
            var sAttName = 'data-load';
            // 正在请求数据中，忽略点击事件
            if (oEl.attr(sAttName) === '1') {
                return;
            }
            // 增加标记，避免请求过程中的频繁点击
            oEl.attr(sAttName, '1');
            that.renderMore(function () {
                // 取消点击标记位，可以进行下一次加载
                oEl.removeAttr(sAttName);
                // 没有数据隐藏加载更多按钮
                !that.listHasNext && oEl.hide();
            });
        });
    }

    function fRenderMore(fCb) {
        var that = this;
        // 没有更多数据，不处理
        if (!that.listHasNext) {
            return;
        }
        that.requestData({
            page: that.page + 1,
            pageSize: that.pageSize,
            call: function (oResult) {
                // 是否有更多数据
                that.listHasNext = !!oResult.has_next && (oResult.images || []).length > 0;
                // 更新当前页面
                that.page++;
                // 渲染数据
                var sHtml = '';
                // $.each(oResult.images,function (nIndex,oImage) {
                //    alert(JSON.stringify(oImage['user'].username));
                // });
                $.each(oResult.images, function (nIndex, oImage) {
                    sHtml += that.tpl([
                            '<article class="mod">',
                            '<header class="mod-hd">',
                                '<time class="time">#{created_date}</time>',
                                '<a href="/profile/'+ oImage.user.id + '" class="avatar">',
                                    '<img src="'+ oImage.user.head_url+ '">',
                                '</a>',
                                '<div class="profile-info">',
                                    '<a title="'+ oImage.user.username+'" href="/profile/'+oImage.user.id+'">'+oImage.user.username+'</a>',
                                '</div>',
                            '</header>',
                            '<div class="mod-bd">',
                                '<div class="img-box">',
                                    '<a href="/image/#{id}">',
                                        '<img src="#{url}">',
                                    '</a>',
                                '</div>',
                            '</div>',
                            '<div class="mod-ft">',
                                '<ul class="discuss-list">',
                                    '<li class="more-discuss">',
                                        '<a>',
                                            '<span>全部 </span><span class="">#{comment_count}</span>',
                                            '<span> 条评论</span></a>',
                                    '</li>'].join(''), oImage);
                    //遍历添加评论
                    $.each(oImage.comments,function (index, oComment) {
                        if(index > 1){return false;}
                        sHtml += that.tpl([
                            '<li>',
                                '<a class="_4zhc5 _iqaka" title="zjuyxy" href="/profile/'+oImage.user.id+'" data-reactid=".0.1.0.0.0.2.1.2:$comment-17856951190001917.1">'+oImage.user.username+'</a>',
                                 '<span>',
                                    '<span>'+oComment.content+'</span>',
                                 '</span>',
                            '</li>'].join(''), oComment);
                    });
                    //分割线
                    sHtml += that.tpl([
                            '</ul>',
                            '<section class="discuss-edit">',
                                '<form>',
                                    '<input placeholder="添加评论..." type="text">',
                                '</form>',
                                '<button class="more-info">提交</button>',
                            '</section>',
                        '</div>',
                    '</article>'].join(''), oImage);
                });
                sHtml && that.listEl.append(sHtml);
            },
            error: function () {
                alert('出现错误，请稍后重试');
            },
            always: fCb
        });
    }

    function fRequestData(oConf) {
        var that = this;
        var sUrl = '/index/images/' + oConf.page + '/' + oConf.pageSize + '/';
        $.ajax({url: sUrl, dataType: 'json'}).done(oConf.call).fail(oConf.error).always(oConf.always);
    }

    function fTpl(sTpl, oData) {
        var that = this;
        sTpl = $.trim(sTpl);
        return sTpl.replace(/#{(.*?)}/g, function (sStr, sName) {
            return oData[sName] === undefined || oData[sName] === null ? '' : oData[sName];
        });
    }
});