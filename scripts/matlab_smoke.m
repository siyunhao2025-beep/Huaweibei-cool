% MATLAB R2024b 真机烟雾测试（Wave4-A）。
% 用法：matlab -batch "run('scripts\matlab_smoke.m')"
% 本脚本只跑最小规模问题，秒级完成；maxNumCompThreads(2) 限制 CPU 占用，
% 避免与用户正在运行的 MATLAB 进程抢资源。
maxNumCompThreads(2);

fprintf('##### MATLAB SMOKE TEST #####\n');

% ---- 定位仓库根 / 工作目录 ----
try
    thisFile = mfilename('fullpath');
    if ~isempty(thisFile)
        repoRoot = fileparts(fileparts(thisFile));  % scripts/ -> 仓库根
    else
        repoRoot = pwd;
    end
catch
    repoRoot = pwd;
end
workDir = fullfile(repoRoot, '_work');
if ~exist(workDir, 'dir'); mkdir(workDir); end
fprintf('repoRoot = %s\n', repoRoot);
fprintf('workDir  = %s\n', workDir);

% ---- 0. locale / 编码（留痕，便于判断中文字面量是否被正确读取）----
try
    loc = feature('locale');
    fprintf('locale.encoding = %s\n', loc.encoding);
    fprintf('locale.codeset  = %s\n', loc.codeset);
catch ME
    fprintf('locale query failed: %s\n', ME.message);
end

% ---- 1. version / ver ----
fprintf('\n=== [1] version & ver ===\n');
fprintf('version: %s\n', version);
v = ver;
fprintf('Installed products (%d):\n', length(v));
for k = 1:length(v)
    fprintf('  - %s\n', v(k).Name);
end

% ---- 2. license('test', ...) 探测工具箱 ----
fprintf('\n=== [2] license test toolboxes ===\n');
tbList = {
    'Optimization_Toolbox',            'Optimization Toolbox';
    'GADS_Toolbox',                    'Global Optimization Toolbox';
    'Statistics_Toolbox',              'Statistics and Machine Learning Toolbox';
    'Deep_Learning_Toolbox',           'Deep Learning Toolbox';
    'Signal_Toolbox',                  'Signal Processing Toolbox';
    'Image_Toolbox',                   'Image Processing Toolbox'};
tbAvailable = struct();
for i = 1:size(tbList, 1)
    feat = tbList{i, 1}; label = tbList{i, 2};
    try
        tf = license('test', feat);
    catch ME
        tf = false;
        fprintf('  %s: license query error (%s)\n', label, ME.message);
    end
    tbAvailable.(matlab.lang.makeValidName(label)) = logical(tf);
    if tf
        fprintf('  %s: available\n', label);
    else
        fprintf('  %s: unavailable\n', label);
    end
end

% ---- 2b. Deep Learning Toolbox 专用探测（只查许可，不跑任何训练）----
fprintf('\n=== [2b] Deep Learning Toolbox dedicated probe ===\n');
% 红线：只 license('test',...) 查一次，绝不调用 trainNetwork/summarize 等训练类 API。
% 本批处理会话已在脚本头 maxNumCompThreads(2)，且不碰用户正在跑的 MATLAB 进程。
try
    dlOK = license('test', 'Deep_Learning_Toolbox');
catch ME
    dlOK = false;
    fprintf('  Deep Learning Toolbox: license query error (%s)\n', ME.message);
end
if dlOK
    fprintf('Deep Learning Toolbox: available (license checked, no training run)\n');
else
    fprintf('Deep Learning Toolbox: unavailable\n');
end
tbAvailable.DeepLearningDedicated = logical(dlOK);

% ---- 3. linprog 极小例 ----
fprintf('\n=== [3] linprog ===\n');
try
    % min  f'*x = -x1 - x2   s.t.  x1+x2<=5, x1<=3, x1,x2>=0
    f  = [-1; -1];
    A  = [1 1; 1 0];
    b  = [5; 3];
    lb = [0; 0];
    opts = optimoptions('linprog', 'Display', 'off');
    [xLin, fvLin, efLin] = linprog(f, A, b, [], [], lb, [], opts);
    fprintf('  linprog exit=%d  x=(%.4f, %.4f)  fval=%.4f  (expect x1=3,x2=2,fval=-5)\n', ...
        efLin, xLin(1), xLin(2), fvLin);
catch ME
    fprintf('  linprog FAILED: %s\n', ME.message);
end

% ---- 4. intlinprog 极小例 ----
fprintf('\n=== [4] intlinprog ===\n');
try
    % min  -x1-x2  s.t. x1+x2<=5, x1<=3, x1,x2 为非负整数
    f      = [-1; -1];
    intcon = [1; 2];
    A      = [1 1; 1 0];
    b      = [5; 3];
    lb     = [0; 0];
    opts = optimoptions('intlinprog', 'Display', 'off');
    [xInt, fvInt, efInt] = intlinprog(f, intcon, A, b, [], [], lb, [], opts);
    fprintf('  intlinprog exit=%d  x=(%d, %d)  fval=%.4f  (expect fval=-5)\n', ...
        efInt, round(xInt(1)), round(xInt(2)), fvInt);
catch ME
    fprintf('  intlinprog FAILED: %s\n', ME.message);
end

% ---- 5. fmincon 极小例 ----
fprintf('\n=== [5] fmincon ===\n');
try
    % min (x1-2)^2 + (x2-3)^2  s.t. x1+x2<=5
    obj = @(x) (x(1)-2)^2 + (x(2)-3)^2;
    A   = [1 1];
    b   = 5;
    x0  = [0; 0];
    opts = optimoptions('fmincon', 'Display', 'off');
    [xFm, fvFm, efFm] = fmincon(obj, x0, A, b, [], [], [], [], [], opts);
    fprintf('  fmincon exit=%d  x=(%.4f, %.4f)  fval=%.6e  (expect x~(2,3), fval~0)\n', ...
        efFm, xFm(1), xFm(2), fvFm);
catch ME
    fprintf('  fmincon FAILED: %s\n', ME.message);
end

% ---- 6. ga 极小例（Global Optimization 可用才跑）----
fprintf('\n=== [6] ga / particleswarm ===\n');
gaAvail = false;
try
    gaAvail = tbAvailable.('GlobalOptimizationToolbox');
catch
end
if gaAvail
    try
        gaObj = @(x) x^2;
        optsGA = optimoptions('ga', 'Display', 'off');
        [xGA, fvGA, efGA] = ga(gaObj, 1, [], [], [], [], -5, 5, [], [], optsGA);
        fprintf('  ga exit=%d  x=%.4f  fval=%.6e  (expect x~0, fval~0)\n', efGA, xGA, fvGA);
    catch ME
        fprintf('  ga FAILED: %s\n', ME.message);
    end
else
    fprintf('  ga skipped: Global Optimization Toolbox unavailable\n');
end

% ---- 7. ode45 极小例 ----
fprintf('\n=== [7] ode45 ===\n');
try
    odeFun = @(t, y) -2*y;
    [tSol, ySol] = ode45(odeFun, [0 5], 1);
    fprintf('  ode45 t(end)=%.4f  y(end)=%.6e  (expected e^-10=%.6e)\n', ...
        tSol(end), ySol(end), exp(-10));
catch ME
    fprintf('  ode45 FAILED: %s\n', ME.message);
end

% ---- 8. 写 .mat ----
fprintf('\n=== [8] write .mat ===\n');
try
    s.scalar = 42;
    s.vec    = [1, 2, 3, 4, 5];
    s.mat    = [1 2 3; 4 5 6; 7 8 9];
    s.name   = 'huaweibei_smoke';
    matPath = fullfile(workDir, 'matlab_test_output.mat');
    save(matPath, 's');
    fprintf('  wrote: %s  (exists=%d)\n', matPath, exist(matPath, 'file'));
catch ME
    fprintf('  write .mat FAILED: %s\n', ME.message);
end

% ---- 9. 写 .csv ----
fprintf('\n=== [9] write .csv ===\n');
try
    T = table((1:3)', [10; 20; 30], 'VariableNames', {'Iteration', 'Objective'});
    csvPath = fullfile(workDir, 'matlab_test_output.csv');
    writetable(T, csvPath);
    fprintf('  wrote: %s  (exists=%d)\n', csvPath, exist(csvPath, 'file'));
catch ME
    fprintf('  write .csv FAILED: %s\n', ME.message);
end

% ---- 10. 中文字体检查 + 中文出图 ----
fprintf('\n=== [10] Chinese font & figure ===\n');
try
    fonts = listfonts;
    hasYaHei = any(contains(fonts, 'YaHei'));
    hasSimHei = any(contains(fonts, 'SimHei'));
    fprintf('  listfonts: Microsoft YaHei present = %d ; SimHei present = %d\n', ...
        hasYaHei, hasSimHei);
    if hasYaHei
        cnFont = 'Microsoft YaHei';
    elseif hasSimHei
        cnFont = 'SimHei';
    else
        cnFont = fonts{1};
        fprintf('  WARNING: no CJK font found, fallback font = %s\n', cnFont);
    end
    fprintf('  using CJK font: %s\n', cnFont);

    fig = figure('Visible', 'off', 'Position', [100 100 640 360]);
    plot(1:5, [3 1 4 1 5], '-o', 'LineWidth', 2);
    title('测试图表：优化结果', 'FontName', cnFont, 'FontSize', 14);
    xlabel('迭代次数', 'FontName', cnFont);
    ylabel('目标值', 'FontName', cnFont);
    set(gca, 'FontName', cnFont);
    grid on;
    pngPath = fullfile(workDir, 'matlab_chinese_test.png');
    print(fig, pngPath, '-dpng', '-r150');
    close(fig);
    fprintf('  wrote Chinese PNG: %s  (exists=%d)\n', pngPath, exist(pngPath, 'file'));
    % 回打一遍标题字面量，便于在日志里核对源文件编码
    fprintf('  title literal check: 测试图表：优化结果\n');
catch ME
    fprintf('  Chinese figure FAILED: %s\n', ME.message);
end

% ---- 11. 完成 ----
fprintf('\n=== MATLAB SMOKE TEST COMPLETE ===\n');
