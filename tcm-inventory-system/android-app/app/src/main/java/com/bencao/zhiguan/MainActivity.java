package com.bencao.zhiguan;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.DownloadManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.view.KeyEvent;
import android.view.MenuItem;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.URLUtil;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

import java.util.ArrayList;
import java.util.List;

public class MainActivity extends AppCompatActivity {

    // ==================== 配置区域 ====================
    // 服务器地址从SharedPreferences读取，用户在设置页面配置
    private String BASE_URL = "";
    private String HOME_URL = "";

    // 默认服务器地址（首次启动时使用，用户可在设置中修改）
    private static final String DEFAULT_BASE_URL = "http://10.0.2.2:5000";

    // 权限请求码
    private static final int PERMISSION_REQUEST_CODE = 100;
    private static final int SETTINGS_REQUEST_CODE = 200;

    // ==================== UI组件 ====================
    private WebView webView;
    private ProgressBar progressBar;
    private SwipeRefreshLayout swipeRefresh;
    private View noNetworkView;
    private TextView errorTitle;
    private TextView errorMessage;
    private TextView retryButton;
    private long exitTime = 0;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 检查是否已配置服务器地址
        if (!checkServerConfig()) {
            // 未配置，跳转到设置页面
            Intent intent = new Intent(this, SettingsActivity.class);
            startActivityForResult(intent, SETTINGS_REQUEST_CODE);
            return;
        }

        setContentView(R.layout.activity_main);

        // 初始化UI
        initViews();

        // 请求必要权限
        requestPermissions();

        // 配置WebView
        setupWebView();

        // 加载首页
        loadHomePage();
    }

    /**
     * 检查服务器地址配置
     * @return 是否已配置
     */
    private boolean checkServerConfig() {
        // 从Intent获取（从设置页面跳转时）
        String urlFromIntent = getIntent().getStringExtra("server_url");
        if (urlFromIntent != null && !urlFromIntent.isEmpty()) {
            BASE_URL = urlFromIntent;
            HOME_URL = BASE_URL + "/index.html";
            return true;
        }

        // 从SharedPreferences读取
        android.content.SharedPreferences prefs = getSharedPreferences(
                SettingsActivity.PREFS_NAME, MODE_PRIVATE);
        String savedUrl = prefs.getString(SettingsActivity.KEY_SERVER_URL, "");

        if (savedUrl != null && !savedUrl.isEmpty()) {
            BASE_URL = savedUrl;
            HOME_URL = BASE_URL + "/index.html";
            return true;
        }

        return false;
    }

    private void initViews() {
        webView = findViewById(R.id.webView);
        progressBar = findViewById(R.id.progressBar);
        swipeRefresh = findViewById(R.id.swipeRefresh);
        noNetworkView = findViewById(R.id.noNetworkView);
        errorTitle = findViewById(R.id.errorTitle);
        errorMessage = findViewById(R.id.errorMessage);
        retryButton = findViewById(R.id.retryButton);

        // 下拉刷新
        swipeRefresh.setOnRefreshListener(() -> webView.reload());

        // 点击重试按钮重新加载
        retryButton.setOnClickListener(v -> loadHomePage());
        // 点击错误视图也重新加载
        noNetworkView.setOnClickListener(v -> loadHomePage());
    }

    private void requestPermissions() {
        List<String> permissionsNeeded = new ArrayList<>();

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.INTERNET)
                != PackageManager.PERMISSION_GRANTED) {
            permissionsNeeded.add(Manifest.permission.INTERNET);
        }

        if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.P) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED) {
                permissionsNeeded.add(Manifest.permission.WRITE_EXTERNAL_STORAGE);
            }
        }

        if (!permissionsNeeded.isEmpty()) {
            ActivityCompat.requestPermissions(this,
                    permissionsNeeded.toArray(new String[0]),
                    PERMISSION_REQUEST_CODE);
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings settings = webView.getSettings();

        // 基础设置
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);

        // 缓存设置（现代WebView默认启用缓存，无需手动设置AppCache）
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        // 缩放设置
        settings.setSupportZoom(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);

        // 其他设置
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setLoadsImagesAutomatically(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        // Cookie支持
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);

        // WebViewClient - 页面加载处理
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();

                // 处理外部链接
                if (url.startsWith("tel:") || url.startsWith("mailto:") || url.startsWith("sms:")) {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                    return true;
                }

                // 处理非HTTP链接
                if (!url.startsWith("http://") && !url.startsWith("https://")) {
                    try {
                        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                        startActivity(intent);
                        return true;
                    } catch (Exception e) {
                        return false;
                    }
                }

                // 同一域名的链接在WebView内打开
                if (url.contains(BASE_URL.replace("http://", "").replace("https://", ""))
                        || url.startsWith(BASE_URL)) {
                    return false;
                }

                // 外部链接用浏览器打开
                Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                startActivity(intent);
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                progressBar.setVisibility(View.VISIBLE);
                hideErrorView();
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                progressBar.setVisibility(View.GONE);
                swipeRefresh.setRefreshing(false);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                if (request.isForMainFrame()) {
                    progressBar.setVisibility(View.GONE);
                    swipeRefresh.setRefreshing(false);
                    // 只要主框架加载失败就显示错误提示（修复白屏问题）
                    showErrorView();
                }
            }
        });

        // WebChromeClient - 进度条和JS对话框
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                super.onProgressChanged(view, newProgress);
                progressBar.setProgress(newProgress);
                if (newProgress >= 100) {
                    progressBar.setVisibility(View.GONE);
                }
            }

            @Override
            public boolean onJsAlert(WebView view, String url, String message,
                                     android.webkit.JsResult result) {
                new AlertDialog.Builder(MainActivity.this)
                        .setTitle("提示")
                        .setMessage(message)
                        .setPositiveButton("确定", (dialog, which) -> result.confirm())
                        .setCancelable(false)
                        .show();
                return true;
            }

            @Override
            public boolean onJsConfirm(WebView view, String url, String message,
                                       android.webkit.JsResult result) {
                new AlertDialog.Builder(MainActivity.this)
                        .setTitle("确认")
                        .setMessage(message)
                        .setPositiveButton("确定", (dialog, which) -> result.confirm())
                        .setNegativeButton("取消", (dialog, which) -> result.cancel())
                        .setCancelable(false)
                        .show();
                return true;
            }
        });

        // 文件下载处理
        webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                // Android 10+ 使用DownloadManager
                DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
                request.setMimeType(mimeType);
                request.addRequestHeader("User-Agent", userAgent);
                request.setDescription("正在下载...");
                request.setTitle(URLUtil.guessFileName(url, contentDisposition, mimeType));
                request.allowScanningByMediaScanner();
                request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS,
                        URLUtil.guessFileName(url, contentDisposition, mimeType));
                DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                if (dm != null) {
                    dm.enqueue(request);
                    Toast.makeText(MainActivity.this, "开始下载...", Toast.LENGTH_SHORT).show();
                }
            } else {
                // 旧版本直接用浏览器下载
                Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                startActivity(intent);
            }
        });
    }

    private void loadHomePage() {
        hideErrorView();
        if (isNetworkAvailable()) {
            webView.loadUrl(HOME_URL);
        } else {
            showErrorView();
            Toast.makeText(this, "网络连接不可用，请检查网络设置", Toast.LENGTH_LONG).show();
        }
    }

    private boolean isNetworkAvailable() {
        ConnectivityManager connectivityManager =
                (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        if (connectivityManager != null) {
            NetworkInfo activeNetworkInfo = connectivityManager.getActiveNetworkInfo();
            return activeNetworkInfo != null && activeNetworkInfo.isConnected();
        }
        return false;
    }

    /**
     * 显示错误提示界面
     * 根据网络状态显示不同的错误信息
     */
    private void showErrorView() {
        runOnUiThread(() -> {
            webView.setVisibility(View.GONE);
            noNetworkView.setVisibility(View.VISIBLE);

            if (!isNetworkAvailable()) {
                // 网络完全不可用
                errorTitle.setText("网络连接不可用");
                errorMessage.setText("请检查手机的网络连接（WiFi或移动数据）后点击重试");
            } else {
                // 网络可用但无法连接服务器
                errorTitle.setText("无法连接到服务器");
                errorMessage.setText("服务器可能未启动或地址配置错误\n当前地址：" + BASE_URL + "\n请检查服务器状态后点击重试");
            }
        });
    }

    /**
     * 隐藏错误提示界面
     */
    private void hideErrorView() {
        runOnUiThread(() -> {
            noNetworkView.setVisibility(View.GONE);
            webView.setVisibility(View.VISIBLE);
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == SETTINGS_REQUEST_CODE) {
            // 从设置页面返回，重新检查配置
            if (checkServerConfig()) {
                // 配置成功，重新创建Activity
                recreate();
            } else {
                // 用户未配置，退出APP
                finish();
            }
        }
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        // 按返回键时，如果WebView可以后退，则后退
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack();
            return true;
        }

        // 双击返回键退出应用
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            if (System.currentTimeMillis() - exitTime > 2000) {
                Toast.makeText(getApplicationContext(), "再按一次退出程序", Toast.LENGTH_SHORT).show();
                exitTime = System.currentTimeMillis();
            } else {
                finish();
                System.exit(0);
            }
            return true;
        }

        return super.onKeyDown(keyCode, event);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSION_REQUEST_CODE) {
            // 权限请求结果处理
            boolean allGranted = true;
            for (int result : grantResults) {
                if (result != PackageManager.PERMISSION_GRANTED) {
                    allGranted = false;
                    break;
                }
            }
            if (!allGranted) {
                Toast.makeText(this, "部分权限被拒绝，可能影响部分功能", Toast.LENGTH_SHORT).show();
            }
        }
    }

    @Override
    public boolean onCreateOptionsMenu(android.view.Menu menu) {
        getMenuInflater().inflate(R.menu.main_menu, menu);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(android.view.MenuItem item) {
        int id = item.getItemId();

        if (id == R.id.action_settings) {
            // 打开服务器设置页面
            Intent intent = new Intent(this, SettingsActivity.class);
            startActivityForResult(intent, SETTINGS_REQUEST_CODE);
            return true;
        }

        if (id == R.id.action_refresh) {
            // 刷新页面
            webView.reload();
            Toast.makeText(this, "正在刷新...", Toast.LENGTH_SHORT).show();
            return true;
        }

        if (id == R.id.action_copy_url) {
            // 复制当前地址
            String currentUrl = webView.getUrl();
            if (currentUrl != null && !currentUrl.isEmpty()) {
                android.content.ClipboardManager clipboard =
                        (android.content.ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                android.content.ClipData clip = android.content.ClipData.newPlainText("URL", currentUrl);
                clipboard.setPrimaryClip(clip);
                Toast.makeText(this, "地址已复制", Toast.LENGTH_SHORT).show();
            }
            return true;
        }

        return super.onOptionsItemSelected(item);
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
        }
        super.onDestroy();
    }
}
