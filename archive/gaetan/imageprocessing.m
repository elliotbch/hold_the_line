%rgb = imread('fruit.png');
%img = imresize(img, 1/16, 'bicubic');
%[X_no_dither,map] = rgb2ind(rgb,8,'nodither');
%imshow(X_no_dither,map)


rgb = imread('line2.jpeg');
%rgb = fliplr(rgb);
%rgb = imrotate(rgb,43)
imshow(rgb);
rgb = imresize(rgb,1/32,"bilinear");
[rgb,map] = rgb2ind(rgb,2,'nodither');
imshow(rgb,map);
angle = trouverAngle(rgb, 0)

function angle = trouverAngle(img, i)
    S = size(img);
    coef = regressionlineair(img, i);
    coef = coef(2);
    coef = 1/coef;
    angle = -mod(atan(coef)*360/(2*pi),180)+90;
    %angle = atan(coef)*360/(2*pi)
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
    coef = x\y;
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


