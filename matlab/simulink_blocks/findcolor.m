% Bloc MATLAB Function « slow/findcolor » extrait de simulink/projects5.slx
% (copie en lecture seule pour consulter l'algorithme sans MATLAB ;
%  la source de référence reste le modèle Simulink).

function [c,tresh] = findcolor(img,n)
    [img,map,D] = quantize(img,n); %quantizing the image

    % Calculate every fit error for each linear regression 
    index = 0;
    listlen = [];
    listerr = [];

    for i=1:n
        [therror,len] = regressionlineair(img,i);
        listerr = [listerr therror];
        listlen = [listlen len];
    end
    minerror = max(listerr, [], 'all');
    for i=1:n
        if listerr(1,i)<minerror & listlen(1,i)~=max(listlen,[],'all') 
            index = i;
            linelen = listlen(1,i);
            minerror = listerr(1,i)/(log(linelen));
        end
    end

    
    %Here we have the right index
    index;
    D(:,index);
    ct = map(index,:);
    c = ct;
    S = size(img);
    min = -1;
    %And then you choose the biggest sphere possible that contain the only 
    %color specified by index
    for i=1:n
        if i~=index  
            for x=1:S(1,1)
                    for y=1:S(1,2)
                        if img(x,y)==i
                            if min ~= -1
                                if sqrt(D(x*y, i))<min
                                    min = sqrt(D(x*y, i));
                                end
                            end
                            min = sqrt(D(x*y, i));
                        end
                    end
            end
        end
    end
    tresh = min;
end

function [coef,len] = regressionlineair(img, i)
    S = size(img);
    Points = [];
    for l=1:S(1,1)
       Points = [ Points trouvermilieux(img,l,i)];
    end
    x = Points(1,:);
    x = transpose(x);
    s = size(x);
    un = ones(s(1,1),1);
    y = Points(2,:);
    y = transpose(y);
    x = double(x);
    y = double(y);
    [p,S] = polyfit(x,y,1);
    f = polyval(p,x);
    SP = size(Points);
    %calculate the fit error ponderate by the square of the line length
    b = sum((y-f).^2);
    %b% = sum((y-f).^2)/SP(1,2);
    %b = sum((y-f).^2)*log(SP(1,2));
    coef = b;
    len = SP(1,2);
end


function pix = trouvermilieux(img, l, i)
    %for each same colors segment of ligne i, find a middle point
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

%% This is the code that give a proof that the matlab uint8() function is a random function. 
% function [img,map,D] = quantize(rgb,k)
% S=size(rgb);
% tmp = ones(3,S(1,1)*S(1,2));
% for l=1:S(1,1)
%     tmp(:,(l-1)*S(1,2)+1:l*S(1,2))=transpose(squeeze(rgb(l,:,:)));
% end
% [idx,C,sumd,D] = kmeans(transpose(tmp),k);
% idx;
% C;
% sumd;
% imgt = ones(S(1,1),S(1,2));
% 
% for i=1:S(1,1)*S(1,2)
%     imgt(uint32(i/S(1,2))+1,mod(i,S(1,2))+1) = idx(i);
% end
% size(imgt);
% %mapt = int32(C);
% imgt;
% imgt(S(1,1)+1,:) = [];
% %imgt = medfilt2(imgt,[8,8]);
% 
% img = uint8(imgt);
% map = uint8(C);
% end
% 

function [img,map,D] = quantize(rgb,k)
S=size(rgb);
tmp = ones(3,S(1,1)*S(1,2));
%get the list of all pixels of the image
for l=1:S(1,1)
    tmp(:,(l-1)*S(1,2)+1:l*S(1,2))=transpose(squeeze(rgb(l,:,:)));
end
[idx,C,~,D] = kmeans(transpose(tmp),k); % compute a k mean function
imgt = ones(S(1,1),S(1,2));

for i=1:(S(1,1)-1)*S(1,2)
    imgt(uint32(i/S(1,2))+1,mod(i,S(1,2))+1) = idx(i);
end
size(imgt);
size(rgb);
img = imgt;
%map = uint8(C);%mieux vaut garder la precision
map = C;
end
