$(".show-more a").on("click", function() {
    var $this = $(this); 
    var $content = $this.parent().prev("div.content");
    var linkText = $this.text().toUpperCase();    
    
    if(linkText === "SHOW MORE"){
        linkText = "Show less";
        $content.switchClass("hideContent", "showContent", 100);
    } else {
        linkText = "Show more";
        $content.switchClass("showContent", "hideContent", 100);
    };

    $this.text(linkText);
});
