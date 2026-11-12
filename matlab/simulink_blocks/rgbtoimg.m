% Bloc MATLAB Function « input/rgbtoimg » extrait de simulink/projects5.slx
% (copie en lecture seule pour consulter l'algorithme sans MATLAB ;
%  la source de référence reste le modèle Simulink).

function img= rgbtoimg(r,g,b)
    S = size(r);
    %As in matlab we deal with images with dimentions (n,m,3), and that
    %simulink input is 3 (n,m) image, we transpose the input to match with
    %the matlab code
    imgt=zeros(S(1,1),S(1,2),3);
    imgt(:,:,1) = r(:,:);
    imgt(:,:,2) = g(:,:);
    imgt(:,:,3) = b(:,:);

    %We apply some average filter to make the k mean easier
    h = fspecial("average",[18,18]);
    imgt(:,:,1) = imfilter(imgt(:,:,1),h);
    imgt(:,:,2) = imfilter(imgt(:,:,2),h);
    imgt(:,:,3) = imfilter(imgt(:,:,3),h);
img = uint8(imgt);
