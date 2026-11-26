// Frida billing hook: query products, select the best available introductory offer, and optionally open checkout.
var dexLoader=null, ctxRef=null, clientRef=null;
var PRODUCTS=["g1.play.20tb","g1.play.ai.pro","g1.30tb"];   // 5x / 20x introductory offer / alternate 20x
var PREFER="";        // Empty selects the longest introductory period; can prefer an offer ID such as "eft-12month".
var ACTIVITY_METHOD="auto"; // auto=choose then ActivityThread; choose/thread force one
function L(v){ Java.classFactory.loader=v; }
function S(o){ send(o); }

function periodRank(p){
  var m={"P1Y6M":18,"P18M":18,"P1Y3M":15,"P15M":15,"P1Y":12,"P12M":12,"P52W1D":12,"P9M":9,"P6M":6,"P26W2D":6,"P180D":6,"P4M":4,"P3M":3,"P13W1D":3,"P2M":2,"P8W6D":2,"P1M":1,"P4W3D":1};
  return m[String(p)]||0;
}
function activityUsable(activity) {
  try {
    if (!activity || activity.isFinishing()) return false;
    // isDestroyed() has existed since API 17; older ROMs may not expose it.
    try { if (activity.isDestroyed()) return false; } catch (_) {}
    return true;
  } catch (e) { return false; }
}
function getActivity(){
  L(null);
  var found=null;
  // Always prefer the original Java.choose implementation when it works.
  if (ACTIVITY_METHOD !== "thread") {
    try {
      Java.choose("android.app.Activity", {
        onMatch:function(a){ if (!found && activityUsable(a)) found=a; },
        onComplete:function(){}
      });
      if (found) {
        S({ev:"activity_selected", method:"choose", name:String(found.getClass().getName())});
        return found;
      }
    } catch (e) {
      S({ev:"choose_err", m:String(e).slice(0,200)});
    }
  }
  if (ACTIVITY_METHOD !== "choose") {
    try {
      // mActivities exists on many Android/ART builds, but is private and
      // may be absent on some devices. Never guess a compatible Activity.
      var Thread=Java.use("android.app.ActivityThread");
      var current=Thread.currentActivityThread();
      if (!current) throw new Error("currentActivityThread unavailable");
      var records=current.mActivities.value;
      if (!records) throw new Error("mActivities unavailable");
      var Record=Java.use("android.app.ActivityThread$ActivityClientRecord");
      var count=records.size();
      for (var i=0;i<count;i++){
        try {
          var rec=Java.cast(records.valueAt(i), Record);
          var act=rec.activity.value;
          if (activityUsable(act)) { found=act; break; }
        } catch (recordErr) {}
      }
      if (found) {
        S({ev:"activity_selected", method:"thread", name:String(found.getClass().getName())});
        return found;
      }
    } catch (e) {
      S({ev:"activity_thread_err", m:String(e).slice(0,200)});
    }
  }
  S({ev:"no_activity", method:ACTIVITY_METHOD});
  return null;
}
function boot(){
 Java.perform(function(){
  try{
   L(null);
   ctxRef=Java.use("android.app.ActivityThread").currentApplication().getApplicationContext();
   var DexClassLoader=Java.use("dalvik.system.DexClassLoader");
   dexLoader=DexClassLoader.$new("/data/local/tmp/module_521.apk",
      ctxRef.getCodeCacheDir().getAbsolutePath(), null, ctxRef.getClassLoader());
   L(dexLoader);
   var BillingClient=Java.use("com.android.billingclient.api.BillingClient");
   var PUL=Java.use("com.android.billingclient.api.PurchasesUpdatedListener");
   var Lst=Java.registerClass({name:"rc.A"+Date.now(), implements:[PUL], methods:{
     onPurchasesUpdated:function(r,p){ S({ev:"purchase_cb", code:r.getResponseCode(), msg:String(r.getDebugMessage()||"")}); }}});
   var b=BillingClient.newBuilder(ctxRef);
   b.setListener(Lst.$new());
   try{ b.enablePendingPurchases(); }catch(e){}
   clientRef=b.build();
   var SLL=Java.use("com.android.billingclient.api.BillingClientStateListener");
   var SL=Java.registerClass({name:"rc.B"+Date.now(), implements:[SLL], methods:{
     onBillingSetupFinished:function(r){ S({ev:"setup", code:r.getResponseCode()});
        if(r.getResponseCode()===0) query(); },
     onBillingServiceDisconnected:function(){ S({ev:"disc"}); }}});
   clientRef.startConnection(SL.$new());
   S({ev:"connecting", products:PRODUCTS});
  }catch(e){ S({ev:"boot_err", m:String(e).slice(0,200)}); }
 });
}
function query(){
 try{
  L(dexLoader);
  var Prod=Java.use("com.android.billingclient.api.QueryProductDetailsParams$Product");
  var Params=Java.use("com.android.billingclient.api.QueryProductDetailsParams");
  var PDL=Java.use("com.android.billingclient.api.ProductDetailsResponseListener");
  var PL=Java.registerClass({name:"rc.C"+Date.now(), implements:[PDL], methods:{
    onProductDetailsResponse:function(res,list){
      S({ev:"pd", code:res.getResponseCode(), n:(list?list.size():0)});
      if(res.getResponseCode()!==0 || !list || list.size()===0) return;
      L(dexLoader);
      var PD=Java.use("com.android.billingclient.api.ProductDetails");
      var SOD=Java.use("com.android.billingclient.api.ProductDetails$SubscriptionOfferDetails");
      var PP=Java.use("com.android.billingclient.api.ProductDetails$PricingPhase");
      var best=null;
      for(var i=0;i<list.size();i++){
        var pd=Java.cast(list.get(i), PD);
        var pid=String(pd.getProductId());
        var offs=pd.getSubscriptionOfferDetails();
        if(!offs){ S({ev:"no_offers", product:pid}); continue; }
        for(var j=0;j<offs.size();j++){
          var o=Java.cast(offs.get(j), SOD);
          var oid=String(o.getOfferId());
          var tok=String(o.getOfferToken());
          var ph=o.getPricingPhases().getPricingPhaseList();
          var first=Java.cast(ph.get(0), PP);
          var micros=String(first.getPriceAmountMicros());
          var period=String(first.getBillingPeriod());
          S({ev:"offer", product:pid, id:oid, micros:micros, period:period, token:tok, title:String(pd.getTitle()), name:String(pd.getName())});
          if(micros!=="0") continue;
          var rank=periodRank(period);
          if(!best || rank>best.rank || (PREFER && oid===PREFER)){
            if(PREFER && oid!==PREFER) continue;
            best={pd:pd, offer:o, product:pid, id:oid, rank:rank, period:period, token:tok};
          }
        }
      }
      if(!best){ S({ev:"no_trial"}); return; }
      S({ev:"chosen", product:best.product, id:best.id, period:best.period});
      if (typeof LIST_ONLY !== "undefined" && LIST_ONLY) {
        S({ev:"list_only", product:best.product, id:best.id, period:best.period, token:best.token});
        return;
      }
      if (typeof OLD_TOKEN !== "undefined" && OLD_TOKEN) {
        S({ev:"stack_start", product:best.product, id:best.id, src:"provided_token"});
        launch(best.pd, best.offer, OLD_TOKEN);
      } else if (typeof STACK !== "undefined" && STACK) {
        S({ev:"stack_start", product:best.product, id:best.id, src:"query"});
        launchWithStack(best.pd, best.offer);
      } else {
        launch(best.pd, best.offer);
      }
    }}});
  var arr=Java.use("java.util.ArrayList").$new();
  for(var k=0;k<PRODUCTS.length;k++){
    arr.add(Prod.newBuilder().setProductId(PRODUCTS[k]).setProductType("subs").build());
  }
  L(dexLoader);
  clientRef.queryProductDetailsAsync(Params.newBuilder().setProductList(arr).build(), PL.$new());
  S({ev:"query_sent"});
 }catch(e){ S({ev:"query_err", m:String(e).slice(0,200)}); }
}
function launchWithStack(pd, offer){
 try{
  L(dexLoader);
  var QP=Java.use("com.android.billingclient.api.QueryPurchasesParams");
  var PRL=Java.use("com.android.billingclient.api.PurchasesResponseListener");
  var cls=Java.registerClass({name:"rc.P"+Date.now(), implements:[PRL], methods:{
    onQueryPurchasesResponse:function(br, purchases){
      try{
        var list=Java.cast(purchases, Java.use("java.util.List"));
        S({ev:"purchases", n:list.size(), code:String(br.getResponseCode())});
        if(br.getResponseCode()!==0 || list.size()===0){ S({ev:"no_purchase"}); return; }
        var Purchase=Java.use("com.android.billingclient.api.Purchase");
        var matching=null;
        for(var p=0;p<list.size();p++){
          var purchase=Java.cast(list.get(p), Purchase);
          if(purchase.getProducts().contains("g1.2tb.ai.subs_variant")){
            matching=purchase; break;
          }
        }
        if(!matching){ S({ev:"no_matching_purchase"}); return; }
        var tok=String(matching.getPurchaseToken());
        S({ev:"old_purchase", head:tok.slice(0,16), products:String(matching.getProducts())});
        launch(pd, offer, tok);
      }catch(e){ S({ev:"stack_query_err", m:String(e).slice(0,200)}); return; }
    }}});
  var qp=QP.newBuilder().setProductType("subs").build();
  clientRef.queryPurchasesAsync(qp, cls.$new());
 }catch(e){ S({ev:"stack_outer_err", m:String(e).slice(0,200)}); return; }
}

function launch(pd, offer, oldTok){
 try{
  L(dexLoader);
  var PDP=Java.use("com.android.billingclient.api.BillingFlowParams$ProductDetailsParams");
  var BFP=Java.use("com.android.billingclient.api.BillingFlowParams");
  var pdp=PDP.newBuilder().setProductDetails(pd).setOfferToken(String(offer.getOfferToken())).build();
  var l=Java.use("java.util.ArrayList").$new(); l.add(pdp);
  var b=BFP.newBuilder().setProductDetailsParamsList(l);
  if(oldTok){
    // Subscription replacement: existing purchaseToken with replacement mode CHARGE_FULL_PRICE (5).
    // The original author expected trial proration; the actual date and billing are decided by Google Play.
    try{
      var SUP=Java.use("com.android.billingclient.api.BillingFlowParams$SubscriptionUpdateParams");
      var md = (typeof STACK_MODE !== "undefined" && STACK_MODE) ? STACK_MODE : 5;
      var sb=SUP.newBuilder();
      // This Billing API build uses setReplaceProrationMode (formerly setReplaceSkusProrationMode).
      var mode_set=false;
      try{ sb=sb.setReplaceProrationMode(md); mode_set=true; }
      catch(e1){
        try{ sb=sb.setReplaceSkusProrationMode(md); mode_set=true; }
        catch(e2){ S({ev:"mode_err", m:String(e2).slice(0,120)}); }
      }
      S({ev:"mode_applied", mode:md, ok:mode_set});
      if(!mode_set){ S({ev:"stack_param_err", m:"Subscription replacement mode unavailable"}); return; }
      var sup=sb.setOldPurchaseToken(String(oldTok)).build();
      b=b.setSubscriptionUpdateParams(sup);
      S({ev:"stack_mode", mode:md, old: String(oldTok).slice(0,16)});
    }catch(e){ S({ev:"stack_param_err", m:String(e).slice(0,160)}); return; }
  }
  var params=b.build();
  var act=getActivity();
  S({ev:"activity", a: act? String(act.getClass().getName()) : "null"});
  if(!act){ S({ev:"no_activity"}); return; }
  L(null);
  var Handler=Java.use("android.os.Handler"); var Looper=Java.use("android.os.Looper");
  var R=Java.registerClass({name:"rc.R"+Date.now(), implements:[Java.use("java.lang.Runnable")], methods:{
    run:function(){
      try{
        L(dexLoader);
        var Activity=Java.use("android.app.Activity");
        var r2=clientRef.launchBillingFlow(Java.cast(act, Activity), params);
        S({ev:"launched", code:r2.getResponseCode(), msg:String(r2.getDebugMessage()||"")});
      }catch(e){ S({ev:"launch_err", m:String(e).slice(0,200)}); }
    }}});
  Handler.$new(Looper.getMainLooper()).post(R.$new());
 }catch(e){ S({ev:"launch_outer_err", m:String(e).slice(0,200)}); }
}
var __tries=0;
var iv=setInterval(function(){
  try{
    L(null);
    var a=Java.use("android.app.ActivityThread").currentApplication();
    __tries++;
    if(a || __tries>10){ clearInterval(iv); S({ev:"boot_start", app:!!a, tries:__tries}); boot(); }
  }catch(e){
    __tries++;
    if(__tries>10){ clearInterval(iv); S({ev:"boot_force", m:String(e).slice(0,120)}); try{ boot(); }catch(e2){ S({ev:"boot_fail", m:String(e2).slice(0,160)}); } }
  }
},400);

