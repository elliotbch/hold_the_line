

rgb = imread('45degre.jpeg');
%rgb = imread('line.jpeg');
%rgb = fliplr(rgb);
%rgb = imrotate(rgb,43)
%imshow(rgb)
%rgb( 100,250,:)
%rgb( 100,250,:)
%imshow(rgb);
%m = rgb2ind(rgb,5,'nodither');
%[rgb,map] = rgb2ind(rgb,2,'nodither');
sound(findsound(rgb,5));

function y = findsound(rgb,n)
    
    rgb = imresize(rgb,1/24,"bilinear");
    angle = trouverAngle(rgb, n);
    w = pulsation(angle(1));
    t = linspace(0,10,10*int16(2*w));
    y = amplitude(angle(1)) * sin(w*t);
end


function amp = amplitude(angle)
    amp = abs(angle(1)/90);
end

function w = pulsation(angle)
    w = 440 + (angle / 90) * 220;
end

function angle = trouverAngle(img, n)
    i = findcolor(img,n);
    [img,map] = rgb2ind(img,n,'nodither');
    imshow(img,map);
    coef = regressionlineair(img, i);
    surete = coef(1,3);
    coef = coef(1,2);
    coef = 1/coef;
    angle = [-mod(atan(coef)*360/(2*pi),180)+90, surete ];
    %angle = atan(coef)*360/(2*pi)
end

function icol = findcolor(img,n)
    [img,map] = rgb2ind(img,n,'nodither');
    index=0;
    minerror = regressionlineair(img,index);
    minerror = minerror(1,3);
    for i=1:n-1
        therror = regressionlineair(img,i);
        therror = therror(1,3);
        if therror<minerror
            minerror = therror;
            index = i;
        end
    end
    icol = index;
end

function coef = regressionlineair(img, i)
    S = size(img);
    Points = [];
    for l=1:S(1,1)
        Points = [ Points trouvermilieux(img,l,i)];
    end
    x = Points(1,:);
    x = transpose(x);
    s = size(x);
    un = ones(s(1,1),1);
    x = [un x];
    x = single(x);
    y = Points(2,:);
    y = transpose(y);
    y = single(y);
    [b, bint, r, rint, stats] = regress(y,x)
    stats;
    %autcoef = regress(y,xe)
    %coef = x\y
    b = [transpose(b) stats(1,4)];
    coef = b;
end


function pix = trouvermilieux(img, l, i)
    S = size(img);
    c = 1;
    temp = [];
    while c<S(1,2)
        while img(l,c)~=i & c < S(1,2)
            c=c+1;
        end

        debut = c;
        while img(l,c)==i & c < S(1,2)
            c=c+1;
        end
        fin = int16(c-1);
        if img(l,debut)==i & img(l,fin)==i
            vec = [l int16((debut+fin)/2)];
            vec = transpose(vec);
            temp = [ temp vec];
        end
    end
    pix = temp;
end




